import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
from typing import Any, Dict, Iterable, Optional, Tuple

import requests
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse

from services.whatsapp_booking_bot_service import WhatsAppBookingBotService
from models import now_iso


meta_whatsapp_router = APIRouter(prefix="/whatsapp/meta", tags=["WhatsApp Meta"])

META_WEBHOOK_VERIFY_TOKEN = os.environ.get("META_WEBHOOK_VERIFY_TOKEN")
META_APP_SECRET = os.environ.get("META_APP_SECRET")
META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get(
    "WHATSAPP_API_URL",
    f"https://graph.facebook.com/{META_GRAPH_API_VERSION}",
).rstrip("/")


def _normalize_sender(value: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", str(value or ""))
    if not 8 <= len(digits) <= 15:
        return None
    return f"+{digits}"


def _verify_signature(raw_body: bytes, supplied_signature: Optional[str]) -> bool:
    if not META_APP_SECRET or not supplied_signature:
        return False
    expected = "sha256=" + hmac.new(
        META_APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, supplied_signature)


def _extract_message_text(message: Dict[str, Any]) -> Optional[str]:
    message_type = str(message.get("type") or "").lower()
    if message_type == "text":
        body = ((message.get("text") or {}).get("body") or "").strip()
        return body or None

    if message_type == "interactive":
        interactive = message.get("interactive") or {}
        button = interactive.get("button_reply") or {}
        list_reply = interactive.get("list_reply") or {}
        return (
            str(button.get("id") or button.get("title") or "").strip()
            or str(list_reply.get("id") or list_reply.get("title") or "").strip()
            or None
        )

    if message_type == "button":
        button = message.get("button") or {}
        return str(button.get("text") or button.get("payload") or "").strip() or None

    return None


def _iter_statuses(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            for status in value.get("statuses") or []:
                yield status


async def _process_status_updates(db: Any, payload: Dict[str, Any]) -> None:
    """Persist Meta delivery lifecycle against the outbound notification wamid."""
    for status in _iter_statuses(payload):
        message_id = str(status.get("id") or "").strip()
        meta_status = str(status.get("status") or "").lower().strip()
        if not message_id or meta_status not in {"sent", "delivered", "read", "failed"}:
            continue

        timestamp = status.get("timestamp")
        errors = status.get("errors") or []
        error_summary = None
        if errors:
            first = errors[0] or {}
            error_summary = str(
                first.get("message")
                or first.get("title")
                or ((first.get("error_data") or {}).get("details"))
                or "Meta reported message delivery failure"
            )[:500]

        now = now_iso()
        update_fields: Dict[str, Any] = {
            "status": meta_status,
            "meta_status": meta_status,
            "status_updated_at": now,
        }
        if timestamp:
            update_fields["meta_status_timestamp"] = str(timestamp)
        if meta_status == "sent":
            update_fields["sent_at"] = now
        elif meta_status == "delivered":
            update_fields["delivered_at"] = now
        elif meta_status == "read":
            update_fields["read_at"] = now
        elif meta_status == "failed":
            update_fields["failed_at"] = now
            update_fields["error_message"] = error_summary

        result = await db.notification_log.update_many(
            {"provider_reference": message_id},
            {"$set": update_fields},
        )
        if result.matched_count:
            logging.info(
                "Meta WhatsApp delivery status updated: status=%s matched=%s",
                meta_status,
                result.matched_count,
            )
        else:
            # Keep unmatched callbacks for diagnosis (for example bot free-text replies
            # that are not represented in notification_log).
            await db.whatsapp_meta_status_events.update_one(
                {"message_id": message_id, "status": meta_status},
                {
                    "$set": {
                        "message_id": message_id,
                        "status": meta_status,
                        "timestamp": str(timestamp or ""),
                        "error_message": error_summary,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )


def _iter_messages(payload: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            for message in value.get("messages") or []:
                yield value, message


async def _send_meta_text(to_e164: str, text: str, phone_number_id: Optional[str] = None) -> None:
    target_phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
    if not target_phone_number_id or not WHATSAPP_ACCESS_TOKEN:
        logging.warning("Meta WhatsApp reply skipped because outbound credentials are not configured")
        return

    recipient = re.sub(r"\D", "", to_e164)
    url = f"{WHATSAPP_API_URL}/{target_phone_number_id}/messages"

    def _send() -> requests.Response:
        return requests.post(
            url,
            headers={
                "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": text},
            },
            timeout=15,
        )

    try:
        response = await asyncio.to_thread(_send)
        if response.status_code not in (200, 201, 202):
            logging.warning(
                "Meta WhatsApp bot reply rejected: status=%s",
                response.status_code,
            )
        else:
            logging.info("Meta WhatsApp bot reply accepted")
    except Exception as exc:
        logging.warning("Meta WhatsApp bot reply failed: %s", exc.__class__.__name__)


async def _process_webhook_payload(db: Any, payload: Dict[str, Any]) -> None:
    # Process outbound delivery receipts before handling inbound conversation messages.
    await _process_status_updates(db, payload)

    for value, message in _iter_messages(payload):
        sender = _normalize_sender(message.get("from"))
        text = _extract_message_text(message)
        message_id = str(message.get("id") or "").strip() or None
        if not sender or not text:
            continue

        if message_id:
            result = await db.whatsapp_meta_inbound_events.update_one(
                {"message_id": message_id},
                {
                    "$setOnInsert": {
                        "message_id": message_id,
                        "sender_hash": hashlib.sha256(sender.encode("utf-8")).hexdigest(),
                        "created_at": now_iso(),
                    }
                },
                upsert=True,
            )
            if result.matched_count > 0 and result.upserted_id is None:
                continue

        reply = await WhatsAppBookingBotService.handle_inbound(db, sender, text)
        if not reply:
            continue

        metadata = value.get("metadata") or {}
        await _send_meta_text(sender, reply, metadata.get("phone_number_id"))


@meta_whatsapp_router.get("/status")
async def meta_whatsapp_status():
    """Non-secret readiness probe for production configuration."""
    return {
        "provider": "meta",
        "webhook_verify_token_configured": bool(META_WEBHOOK_VERIFY_TOKEN),
        "app_secret_configured": bool(META_APP_SECRET),
        "phone_number_id_configured": bool(WHATSAPP_PHONE_NUMBER_ID),
        "access_token_configured": bool(WHATSAPP_ACCESS_TOKEN),
        "graph_api_version": META_GRAPH_API_VERSION,
        "ready": bool(
            META_WEBHOOK_VERIFY_TOKEN
            and META_APP_SECRET
            and WHATSAPP_PHONE_NUMBER_ID
            and WHATSAPP_ACCESS_TOKEN
        ),
    }


@meta_whatsapp_router.get("/webhook")
async def verify_meta_webhook(request: Request):
    if not META_WEBHOOK_VERIFY_TOKEN:
        raise HTTPException(status_code=503, detail="Meta webhook verification is not configured")

    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if (
        mode == "subscribe"
        and verify_token
        and challenge is not None
        and hmac.compare_digest(verify_token, META_WEBHOOK_VERIFY_TOKEN)
    ):
        return PlainTextResponse(challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@meta_whatsapp_router.post("/webhook")
async def receive_meta_webhook(request: Request, background_tasks: BackgroundTasks):
    if not META_APP_SECRET:
        raise HTTPException(status_code=503, detail="Meta webhook signature verification is not configured")

    raw_body = await request.body()
    if not _verify_signature(raw_body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    # Meta expects a prompt 200 response. Booking-bot work runs after acknowledgement.
    background_tasks.add_task(_process_webhook_payload, request.app.state.db, payload)
    return {"status": "accepted"}
