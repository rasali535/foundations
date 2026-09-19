import asyncio
import logging
import os
import re
from typing import Any, Dict, Optional

import requests

from models import NotificationLog, now_iso
from services.audit_service import AuditService


META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get(
    "WHATSAPP_API_URL", f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
).rstrip("/")
WHATSAPP_TEMPLATE_LANGUAGE = os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "en")

# Canonical Foundations template catalogue. Keep these names aligned with Meta.
TEMPLATES = {
    "intake_received": "fca_intake_received",
    "booking_confirmation": "fca_booking_confirmation",
    "booking_reminder_24h": "fca_booking_reminder_24h",
    "booking_reminder_2h": "fca_booking_reminder_2h",
    "booking_rescheduled": "fca_booking_rescheduled",
    "booking_cancelled": "fca_booking_cancelled",
    "virtual_session_confirmation": "fca_virtual_session_confirmation",
    "virtual_session_link": "fca_virtual_session_link",
    "followup_booking": "fca_followup_booking",
    "payment_reminder": "fca_payment_reminder",
    "payment_received": "fca_payment_received",
}


def _recipient(phone: Optional[str]) -> Optional[str]:
    raw = str(phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return digits
    return None


def _safe_error(response: requests.Response) -> str:
    try:
        body = response.json()
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            return f"HTTP {response.status_code}: {str(error.get('message') or error.get('code') or 'Meta rejected request')[:180]}"
    except Exception:
        pass
    return f"HTTP {response.status_code}"


class MetaWhatsAppTemplateService:
    """Privacy-conscious sender for approved Foundations utility templates."""

    @staticmethod
    def configured() -> bool:
        return bool(WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN)

    @staticmethod
    async def send(
        db: Any,
        *,
        phone: str,
        event: str,
        variables: Dict[str, Any],
        client_id: str,
        booking_id: Optional[str] = None,
        booking_batch_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> NotificationLog:
        template_name = TEMPLATES.get(event)
        recipient = _recipient(phone)
        log = NotificationLog(
            client_id=client_id,
            booking_id=booking_id,
            booking_batch_id=booking_batch_id,
            channel="whatsapp",
            recipient=phone or "None",
            template=template_name or event,
            subject=f"WhatsApp {event.replace('_', ' ').title()}",
            content_summary=f"Foundations utility event: {event}",
            status="pending",
            created_at=now_iso(),
        )

        if not template_name:
            log.status = "failed"
            log.error_message = f"Unknown Foundations WhatsApp event '{event}'"
        elif not recipient:
            log.status = "failed"
            log.error_message = "Client phone must be stored in international E.164 format"
        elif not MetaWhatsAppTemplateService.configured():
            log.status = "failed"
            log.error_message = "Meta WhatsApp Cloud API is not configured"
        else:
            parameters = [
                {
                    "type": "text",
                    "parameter_name": name,
                    "text": str(value),
                }
                for name, value in variables.items()
                if value is not None
            ]
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language or WHATSAPP_TEMPLATE_LANGUAGE},
                    "components": [{"type": "body", "parameters": parameters}],
                },
            }
            url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

            def _post():
                return requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15,
                )

            try:
                response = await asyncio.to_thread(_post)
                if response.status_code in (200, 201, 202):
                    body = response.json() if response.content else {}
                    messages = body.get("messages") if isinstance(body, dict) else None
                    provider_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
                    log.status = "sent"
                    log.sent_at = now_iso()
                    log.provider_reference = provider_id or "meta-accepted"
                else:
                    log.status = "failed"
                    log.error_message = _safe_error(response)
            except Exception as exc:
                logging.warning("Meta utility template send failed: %s", exc.__class__.__name__)
                log.status = "failed"
                log.error_message = f"Meta WhatsApp delivery error: {exc.__class__.__name__}"

        await db.notification_log.insert_one(log.model_dump())
        await AuditService.log_activity(
            db,
            action=f"whatsapp_{'sent' if log.status == 'sent' else 'failed'}",
            client_id=client_id,
            booking_id=booking_id,
            booking_batch_id=booking_batch_id,
            metadata={"provider": "meta", "template": log.template, "event": event},
        )
        return log
