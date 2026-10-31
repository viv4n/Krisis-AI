import logging
from typing import Any, Optional
from fastapi import APIRouter, Request, status
from app.core.config import settings
from app.models.schemas import ReportCreateRequest, ReportCreateResponse
from app.api.v1.endpoints import process_5step_pipeline
from app.services.location import extract_location_from_text
from app.services.triage import get_all_clusters
from app.core.ws import manager

logger = logging.getLogger("krisis.textbee")
router = APIRouter()


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Textbee SMS Webhook Ingestion"
)
async def textbee_webhook(request: Request):
    """
    Textbee Webhook:
    1. Parse incoming JSON containing `sender` (phone number) and `message` (the SMS text).
    2. Set image_base64 to None (SMS lacks media).
    3. Extract explicit coordinates from text (e.g. '29.76, -95.36') or Houston landmark/fallback.
    4. Pass payload to 5-step ML triage pipeline (relies purely on DistilBERT for NLP urgency).
    5. Broadcast incident with guaranteed lat and lng.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON format"}

    sender = body.get("sender") or body.get("from") or body.get("phone") or "Unknown"
    message_text = body.get("message") or body.get("text") or body.get("body") or ""
    message_text = str(message_text).strip()

    if not message_text:
        message_text = f"Empty incident message received from {sender}"

    # Extract location from text (explicit coordinates, landmark, or Houston random offset fallback)
    lat, lon = extract_location_from_text(message_text)

    # Standardize to ReportCreateRequest with source='sms'
    report_req = ReportCreateRequest(
        image_base64=None,
        text=message_text,
        latitude=lat,
        longitude=lon,
        source="sms"
    )

    logger.info(f"Ingesting Textbee SMS from {sender} at ({lat}, {lon}): '{message_text}'")

    # Pass to 5-step ML triage pipeline
    pipeline_res: ReportCreateResponse = await process_5step_pipeline(report_req)

    # Force explicit SMS WebSocket broadcast with guaranteed coordinates
    try:
        updated_clusters = get_all_clusters()
        await manager.broadcast({
            "type": "SMS_INCIDENT",
            "report_id": pipeline_res.report_id,
            "status": pipeline_res.status,
            "triage_status": pipeline_res.status,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lng": lon,
            "text": message_text,
            "incidents": updated_clusters
        })
    except Exception as e:
        logger.error(f"SMS explicit broadcast error: {e}")

    return {
        "status": "ok",
        "sender": sender,
        "report_id": pipeline_res.report_id,
        "triage_status": pipeline_res.status,
        "latitude": lat,
        "longitude": lon,
        "lat": lat,
        "lng": lon,
        "message": pipeline_res.message
    }
