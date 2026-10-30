import uuid
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    ReportCreateRequest,
    ReportCreateResponse,
    IncidentClusterResponse,
    RoutePassabilityResponse
)
from app.services.forensic import verify_image_authenticity
from app.services.triage import (
    classify_hazard,
    calculate_nlp_urgency,
    calculate_visual_damage,
    calculate_infrastructure_proximity_score,
    calculate_priority_score,
    check_uncertainty_escalation,
    merge_or_create_cluster,
    get_all_clusters,
    get_route_passabilities,
    DB_PATH
)

router = APIRouter()


@router.post(
    "/report",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Incident Report"
)
def submit_report(payload: ReportCreateRequest):
    """
    Execute forensic check -> spatial deduplication -> triage scoring.
    Return status: 'success', 'quarantined', or 'escalated'.
    """
    report_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Step 1: Ingestion & Adversarial Defense
    forensic_res = verify_image_authenticity(payload.image_base64)
    if not forensic_res.get("is_valid", True) or forensic_res.get("quarantined", False):
        # Quarantine the report
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, created_at)
            VALUES (?, NULL, ?, ?, ?, ?, 'quarantined', 0.0, ?)
        """, (report_id, payload.text, payload.latitude, payload.longitude, payload.source, now_iso))
        conn.commit()
        conn.close()

        reason_msg = forensic_res.get("reason") or "Media flagged for synthetic generation or tampering."
        return ReportCreateResponse(
            status="quarantined",
            report_id=report_id,
            message=f"Report quarantined by forensic adversarial defense filter: {reason_msg}"
        )

    # Step 2: Triage Assessment
    has_image = bool(payload.image_base64)
    visual_clarity = forensic_res.get("visual_clarity_score", 0.8)
    visual_confidence = visual_clarity if has_image else 0.0

    visual_dmg = calculate_visual_damage(has_image, visual_clarity, payload.text)
    nlp_urgency = calculate_nlp_urgency(payload.text)
    infra_proximity = calculate_infrastructure_proximity_score(payload.latitude, payload.longitude)
    priority_score = calculate_priority_score(visual_dmg, nlp_urgency, infra_proximity)

    hazard_type = classify_hazard(payload.text)
    uncertainty_escalated = check_uncertainty_escalation(has_image, visual_confidence, payload.text)

    # Step 3: Spatial Clustering & Storage
    cluster_id, was_merged = merge_or_create_cluster(
        lat=payload.latitude,
        lon=payload.longitude,
        hazard_type=hazard_type,
        priority_score=priority_score,
        uncertainty_escalated=uncertainty_escalated,
        now_iso=now_iso
    )

    report_status = "escalated" if uncertainty_escalated else "success"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reports (report_id, cluster_id, text, latitude, longitude, source, status, priority_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, cluster_id, payload.text, payload.latitude, payload.longitude, payload.source, report_status, priority_score, now_iso))
    conn.commit()
    conn.close()

    cluster_action = "merged into existing cluster" if was_merged else "assigned new cluster"
    msg = f"Report processed ({cluster_action} {cluster_id}). Priority score: {priority_score}."
    if uncertainty_escalated:
        msg += " Escalated due to high-urgency keywords under visual uncertainty."

    return ReportCreateResponse(
        status=report_status,
        report_id=report_id,
        message=msg
    )


@router.get(
    "/incidents",
    response_model=list[IncidentClusterResponse],
    summary="Get Incident Clusters"
)
def get_incidents():
    """
    Return all active clusters sorted by priority_score descending.
    """
    clusters = get_all_clusters()
    return clusters


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
    routes = get_route_passabilities()
    return routes

