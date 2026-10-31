import base64
import logging
from typing import Any, Optional
import requests
from fastapi import APIRouter, Request, status
from app.core.config import settings
from app.models.schemas import ReportCreateRequest, ReportCreateResponse
from app.api.v1.endpoints import process_5step_pipeline
from app.services.location import extract_location_from_text
from app.services.triage import get_all_clusters
from app.core.ws import manager

logger = logging.getLogger("krisis.telegram")
router = APIRouter()


def send_telegram_message(chat_id: int | str, text: str):
    """Sends confirmation text message back to the Telegram user via Bot API."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.info(f"TELEGRAM_BOT_TOKEN not configured. Skipping outbound message to chat {chat_id}.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=8)
        if resp.status_code != 200:
            logger.warning(f"Telegram sendMessage returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"Error sending Telegram reply: {e}")


def fetch_telegram_photo_bytes(file_id: str) -> Optional[bytes]:
    """Fetches full image bytes for a Telegram file_id using getFile and download."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Cannot fetch Telegram photo.")
        return None

    get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    try:
        resp = requests.get(get_file_url, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Failed to getFile from Telegram API: {resp.status_code}")
            return None

        data = resp.json()
        if not data.get("ok"):
            logger.error(f"Telegram getFile returned not OK: {data}")
            return None

        file_path = data.get("result", {}).get("file_path")
        if not file_path:
            return None

        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        dl_resp = requests.get(download_url, timeout=15)
        if dl_resp.status_code == 200:
            return dl_resp.content
        else:
            logger.error(f"Failed to download image file from {download_url}: {dl_resp.status_code}")
    except Exception as e:
        logger.error(f"Exception downloading Telegram photo {file_id}: {e}")

    return None


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Telegram Webhook Ingestion"
)
async def telegram_webhook(request: Request):
    """
    Telegram Webhook:
    1. Parse incoming Telegram JSON for message.text, message.caption, message.location, and message.photo.
    2. Extract explicit coordinates from caption/text regex, direct GPS location, or Houston fallback.
    3. If photo exists, fetch file_id via Telegram getFile and download bytes into memory.
    4. Standardize payload into ReportCreateRequest and pass to 5-step ML triage pipeline.
    5. Force explicit WebSocket broadcast with guaranteed lat and lng.
    6. Return 200 OK and send confirmation message back to user via Telegram API.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return {"status": "ok", "message": "Ignored invalid JSON"}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"status": "ok", "message": "No message field found"}

    chat_id = message.get("chat", {}).get("id")

    # 1. Extract text or caption
    raw_text = message.get("caption") or message.get("text") or ""
    text_content = str(raw_text).strip() if raw_text else ""
    if not text_content:
        text_content = "Disaster incident reported via Telegram"

    # 2. Extract location / GPS: Direct location or regex extraction from caption with Houston fallback
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Check direct Telegram GPS location attachment
    location = message.get("location")
    if isinstance(location, dict) and "latitude" in location and "longitude" in location:
        try:
            cand_lat = float(location["latitude"])
            cand_lon = float(location["longitude"])
            if -90.0 <= cand_lat <= 90.0 and -180.0 <= cand_lon <= 180.0:
                lat = round(cand_lat, 6)
                lon = round(cand_lon, 6)
        except (ValueError, TypeError):
            pass

    # If no direct GPS attachment, parse caption for explicit coordinates (e.g. "29.76, -95.36") or Houston fallback
    if lat is None or lon is None:
        lat, lon = extract_location_from_text(raw_text)

    # 3. Extract photo (Telegram sends list of PhotoSizes; highest resolution is last)
    photos = message.get("photo")
    image_b64: Optional[str] = None
    if photos and isinstance(photos, list) and len(photos) > 0:
        highest_res_photo = photos[-1]
        if isinstance(highest_res_photo, dict):
            file_id = highest_res_photo.get("file_id")
            if file_id:
                img_bytes = fetch_telegram_photo_bytes(file_id)
                if img_bytes:
                    image_b64 = base64.b64encode(img_bytes).decode("utf-8")

    # Standardize to ReportCreateRequest
    report_req = ReportCreateRequest(
        image_base64=image_b64,
        text=text_content,
        latitude=lat,
        longitude=lon,
        source="web"
    )

    # Pass to 5-step ML pipeline (YOLOv8 + DistilBERT + consensus + broadcast)
    pipeline_res: ReportCreateResponse = await process_5step_pipeline(report_req)

    # Force explicit Telegram WebSocket broadcast with guaranteed coordinates
    try:
        updated_clusters = get_all_clusters()
        await manager.broadcast({
            "type": "TELEGRAM_INCIDENT",
            "report_id": pipeline_res.report_id,
            "status": pipeline_res.status,
            "triage_status": pipeline_res.status,
            "latitude": lat,
            "longitude": lon,
            "lat": lat,
            "lng": lon,
            "text": text_content,
            "incidents": updated_clusters
        })
    except Exception as e:
        logger.error(f"Telegram explicit broadcast error: {e}")

    # Send confirmation back to user if chat_id is available
    if chat_id:
        status_emoji = "⚠️" if pipeline_res.status == "escalated" else "✅"
        reply_msg = (
            f"<b>{status_emoji} Krisis AI Emergency Triage</b>\n"
            f"<b>Status:</b> {pipeline_res.status.upper()}\n"
            f"<b>Report ID:</b> <code>{pipeline_res.report_id}</code>\n"
            f"<b>Location:</b> {lat:.4f}, {lon:.4f}\n\n"
            f"{pipeline_res.message}"
        )
        send_telegram_message(chat_id, reply_msg)

    return {
        "status": "ok",
        "report_id": pipeline_res.report_id,
        "triage_status": pipeline_res.status,
        "latitude": lat,
        "longitude": lon,
        "lat": lat,
        "lng": lon
    }
