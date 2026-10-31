import logging
import sqlite3
import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.models.schemas import (
    ReportCreateRequest,
    ReportCreateResponse,
    IncidentClusterResponse,
    RoutePassabilityResponse
)
from app.services.forensic import verify_image_authenticity
from app.services.vision import assess_damage
from app.services.nlp import assess_urgency
from app.services.triage import (
    classify_hazard,
    calculate_infrastructure_proximity_score,
    calculate_priority_score,
    check_uncertainty_escalation,
    find_duplicate_by_phash,
    check_ai_safety_net_spam,
    merge_into_existing_cluster,
    merge_or_create_cluster,
    get_cluster_by_id,
    get_all_clusters,
    get_route_passabilities,
    DB_PATH
)
from app.core.ws import manager

logger = logging.getLogger("krisis.endpoints")
router = APIRouter()


async def process_5step_pipeline(payload: ReportCreateRequest) -> ReportCreateResponse:
    """
    Orchestrate the 5-Step ML Ingestion Pipeline with AI Safety Net & pHash Deduplication:
    Step 1 (Ingestion): Accept payload from Web, Telegram, or Textbee.
    Step 2 (Sanitization & AI Safety Net):
          - Pre-inference validation for non-emergency spam / chit-chat.
          - pHash computation & Hamming distance deduplication (threshold < 5).
          - Forensic deepfake detection (quarantine synthetic media).
    Step 3 (Inference): Pass image to YOLOv8 (assess_damage) and text to DistilBERT (assess_urgency).
    Step 4 (Spatial Consensus & Scoring):
          - Calculate Priority Score.
          - Post-inference AI Safety Net: discard/reject if score < 10.0 (database status: REJECTED).
          - Cluster assignment: attach to duplicate cluster_id or run 50m Haversine merge/create.
    Step 5 (Scoring & Escalation):
          - Trigger Uncertainty Escalation if visual conf < 0.50 but NLP urgency is high.
          - Save to SQLite reports table.
          - Broadcast new report & cluster data over WebSocket to live UI clients.
    """
    report_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ----------------------------------------------------
    # Step 1: Ingestion
    # ----------------------------------------------------
    logger.info(f"[Step 1] Ingesting report {report_id} from {payload.source} at ({payload.latitude}, {payload.longitude})")

    # ----------------------------------------------------
    # Step 2: Sanitization & Pre-Inference AI Safety Net
    # ----------------------------------------------------
    # AI Safety Net: Noise & Spam Filter before heavy ML inference
    is_spam, spam_reason = check_ai_safety_net_spam(payload.text)
    if is_spam:
        logger.info(f"[AI Safety Net] Report {report_id} flagged as spam/noise: {spam_reason}. Rejecting.")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, phash, created_at)
            VALUES (?, NULL, ?, ?, ?, ?, 'REJECTED', 0.0, NULL, ?)
        """, (report_id, payload.text, payload.latitude, payload.longitude, payload.source, now_iso))
        conn.commit()
        conn.close()

        return ReportCreateResponse(
            status="quarantined",
            report_id=report_id,
            message=f"Report rejected by AI safety net: {spam_reason} (database status: REJECTED)."
        )

    # Forensic Image Verification & pHash Calculation
    forensic_res = verify_image_authenticity(payload.image_base64)
    image_bytes = forensic_res.get("image_bytes") if forensic_res else None
    phash: Optional[str] = forensic_res.get("phash") if forensic_res else None

    # Deepfake / tampering defense check
    if not forensic_res.get("is_valid", True) or forensic_res.get("quarantined", False):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, phash, created_at)
            VALUES (?, NULL, ?, ?, ?, ?, 'quarantined', 0.0, ?, ?)
        """, (report_id, payload.text, payload.latitude, payload.longitude, payload.source, phash, now_iso))
        conn.commit()
        conn.close()

        reason = forensic_res.get("reason") or "Media flagged for synthetic generation or tampering."
        logger.warning(f"[Step 2] Report {report_id} quarantined: {reason}")
        return ReportCreateResponse(
            status="quarantined",
            report_id=report_id,
            message=f"Report quarantined by forensic adversarial defense filter: {reason}"
        )

    # pHash Deduplication with Hamming Distance (< 5)
    is_duplicate = False
    matched_cluster_id = None
    if phash:
        is_duplicate, dup_report_id, matched_cluster_id = find_duplicate_by_phash(phash, threshold=5)
        if is_duplicate:
            logger.info(f"[Step 2] Duplicate image detected via Hamming distance (matched report {dup_report_id}, cluster {matched_cluster_id}).")

    # ----------------------------------------------------
    # Step 3: Inference (YOLOv8 + DistilBERT)
    # ----------------------------------------------------
    has_image = bool(image_bytes)
    visual_damage, visual_confidence = assess_damage(image_bytes)
    nlp_urgency, contains_critical = assess_urgency(payload.text)

    logger.info(f"[Step 3] Inference: visual_damage={visual_damage}, visual_conf={visual_confidence}, nlp_urgency={nlp_urgency}")

    # ----------------------------------------------------
    # Step 4: Spatial Consensus, Scoring & Post-Inference Filter
    # ----------------------------------------------------
    hazard_type = classify_hazard(payload.text)
    infra_proximity = calculate_infrastructure_proximity_score(payload.latitude, payload.longitude)
    priority_score = calculate_priority_score(visual_damage, nlp_urgency, infra_proximity)

    # AI Safety Net: Minimum priority threshold check (< 10)
    if priority_score < 10.0:
        logger.info(f"[AI Safety Net] Report {report_id} has priority score {priority_score} < 10.0. Discarding.")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, phash, created_at)
            VALUES (?, NULL, ?, ?, ?, ?, 'DISCARDED', ?, ?, ?)
        """, (report_id, payload.text, payload.latitude, payload.longitude, payload.source, priority_score, phash, now_iso))
        conn.commit()
        conn.close()

        return ReportCreateResponse(
            status="quarantined",
            report_id=report_id,
            message="Report discarded by AI safety net: priority score below minimum threshold (< 10.0). Database status: DISCARDED."
        )

    # ----------------------------------------------------
    # Step 5: Scoring, Escalation, Consensus & Broadcast
    # ----------------------------------------------------
    uncertainty_escalated = check_uncertainty_escalation(
        has_image=has_image,
        visual_confidence=visual_confidence,
        text=payload.text,
        nlp_urgency=nlp_urgency,
        contains_critical=contains_critical
    )

    # Assign cluster: use matched duplicate cluster if found, or 50m spatial consensus
    if is_duplicate and matched_cluster_id:
        cluster_id = matched_cluster_id
        was_merged = merge_into_existing_cluster(cluster_id, priority_score, uncertainty_escalated, now_iso)
        if not was_merged:
            cluster_id, was_merged = merge_or_create_cluster(
                lat=payload.latitude,
                lon=payload.longitude,
                hazard_type=hazard_type,
                priority_score=priority_score,
                uncertainty_escalated=uncertainty_escalated,
                now_iso=now_iso
            )
    else:
        cluster_id, was_merged = merge_or_create_cluster(
            lat=payload.latitude,
            lon=payload.longitude,
            hazard_type=hazard_type,
            priority_score=priority_score,
            uncertainty_escalated=uncertainty_escalated,
            now_iso=now_iso
        )

    report_status = "escalated" if uncertainty_escalated else "success"

    # Save individual report to SQLite reports database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, phash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, cluster_id, payload.text, payload.latitude, payload.longitude, payload.source, report_status, priority_score, phash, now_iso))
    conn.commit()
    conn.close()

    # Retrieve updated cluster details for broadcasting
    cluster_info = get_cluster_by_id(cluster_id)
    updated_clusters = get_all_clusters()

    new_report_json = {
        "report_id": report_id,
        "cluster_id": cluster_id,
        "text": payload.text,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "lat": payload.latitude,
        "lng": payload.longitude,
        "source": payload.source,
        "status": report_status,
        "priority_score": priority_score,
        "phash": phash,
        "created_at": now_iso,
        "is_duplicate": is_duplicate,
        **(cluster_info or {})
    }

    # Execute WebSocket broadcast to all connected frontend clients
    try:
        broadcast_data = {
            "type": "NEW_REPORT",
            "report": new_report_json,
            "new_report": new_report_json,
            "incident": cluster_info,
            "incidents": updated_clusters,
            **new_report_json
        }
        await manager.broadcast(broadcast_data)
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")

    action_str = "merged into duplicate cluster" if is_duplicate else ("merged into spatial cluster" if was_merged else "created new cluster")
    msg = f"Report processed ({action_str} {cluster_id}). Priority score: {priority_score}."
    if uncertainty_escalated:
        msg += " Escalated due to high NLP urgency under visual uncertainty."

    return ReportCreateResponse(
        status=report_status,
        report_id=report_id,
        message=msg
    )


@router.post(
    "/report",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Incident Report"
)
async def submit_report(payload: ReportCreateRequest):
    """
    Standard HTTP report submission executing the 5-step ML pipeline.
    """
    return await process_5step_pipeline(payload)


@router.get(
    "/incidents",
    response_model=list[IncidentClusterResponse],
    summary="Get Incident Clusters"
)
def get_incidents():
    """
    Return all active clusters sorted by priority_score descending.
    """
    return get_all_clusters()


@router.get(
    "/routes/passability",
    response_model=list[RoutePassabilityResponse],
    summary="Get Route Passability"
)
def get_route_passability():
    """
    Return pre-configured road segments (including hospital arterial roads)
    with dynamic blocked/passable/degraded statuses based on active clusters.
    """
    return get_route_passabilities()
