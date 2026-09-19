import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import Booking, CRMClient, NotificationLog, now_iso
from services.audit_service import AuditService
from services.therapist_service import DEFAULT_THERAPISTS, normalize_e164


META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", f"https://graph.facebook.com/{META_GRAPH_API_VERSION}").rstrip("/")
WHATSAPP_THERAPIST_TEMPLATE_NAME = os.environ.get(
    "WHATSAPP_THERAPIST_TEMPLATE_NAME", "fca_therapist_booking_confirmation"
)
WHATSAPP_TEMPLATE_LANGUAGE = os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "en")
CAT_TZ = ZoneInfo("Africa/Gaborone")


def _mask_recipient(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) >= 7:
        return digits[:3] + "****" + digits[-2:]
    return "***"


def _format_booking_datetime(value: str) -> tuple[str, str]:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(CAT_TZ)
    return dt.strftime("%a %d %b %Y"), dt.strftime("%H:%M CAT")


def _safe_provider_error(response: Optional[requests.Response] = None, exc: Optional[Exception] = None) -> str:
    if response is not None:
        detail = f"HTTP {response.status_code}"
        try:
            body = response.json()
            if isinstance(body, dict):
                message = body.get("detail") or body.get("message") or body.get("error")
                if message:
                    detail += f" {str(message)[:180]}"
        except Exception:
            pass
        return detail
    if exc is not None:
        return exc.__class__.__name__
    return "Unknown provider error"


class TherapistNotificationService:
    @staticmethod
    async def _resolve_notification_target(
        db: AsyncIOMotorDatabase,
        therapist: Any
    ) -> Dict[str, Any]:
        """
        Resolve notification settings from the latest therapist document.

        Historical production data can contain duplicate records for the two seeded FCA
        clinicians. If a booking references a legacy duplicate without notification
        settings, use the canonical seeded record only when the exact clinician name
        matches and that canonical record has explicitly enabled, valid WhatsApp settings.
        This avoids guessing or routing by fuzzy name while preserving old booking IDs.
        """
        therapist_id = getattr(therapist, "id", None)
        therapist_name = str(getattr(therapist, "name", "") or "").strip()

        current: Optional[Dict[str, Any]] = None
        if therapist_id:
            current = await db.therapists.find_one({"id": therapist_id}, {"_id": 0})

        if current:
            current_phone = normalize_e164(current.get("whatsapp_phone"))
            if current.get("whatsapp_notifications_enabled") and current_phone:
                return current

        canonical_template = next(
            (
                item for item in DEFAULT_THERAPISTS
                if str(item.get("name", "")).strip().casefold() == therapist_name.casefold()
            ),
            None
        )
        if canonical_template and canonical_template.get("id") != therapist_id:
            canonical = await db.therapists.find_one(
                {
                    "id": canonical_template.get("id"),
                    "archived_at": {"$exists": False}
                },
                {"_id": 0}
            )
            if canonical:
                canonical_phone = normalize_e164(canonical.get("whatsapp_phone"))
                if canonical.get("whatsapp_notifications_enabled") and canonical_phone:
                    logging.info(
                        "Using canonical therapist notification settings for legacy therapist id %s -> %s",
                        therapist_id,
                        canonical.get("id")
                    )
                    return canonical

        return current or {
            "id": therapist_id,
            "name": therapist_name,
            "whatsapp_phone": getattr(therapist, "whatsapp_phone", None),
            "whatsapp_notifications_enabled": bool(
                getattr(therapist, "whatsapp_notifications_enabled", False)
            )
        }

    @staticmethod
    def build_booking_whatsapp_content(
        therapist: Any,
        client: CRMClient,
        bookings: List[Booking]
    ) -> str:
        first = bookings[0]
        mode = "In-Person" if first.session_mode == "in_person" else "Virtual"
        client_name = f"{client.first_name} {client.last_name}".strip() or "Client"

        lines = [
            "FCA booking assigned.",
            f"Client: {client_name} ({client.client_number})",
            f"Session: {first.session_type.capitalize()}",
            f"Mode: {mode}",
            "Appointments:"
        ]

        for idx, booking in enumerate(bookings, 1):
            date_str, time_str = _format_booking_datetime(booking.starts_at)
            lines.append(f"{idx}. {date_str} at {time_str}")
            if booking.session_mode == "virtual" and booking.virtual_meeting_link:
                lines.append(f"   Meeting link: {booking.virtual_meeting_link}")
            elif booking.session_mode == "virtual":
                lines.append("   Virtual access details are not yet set.")
            elif booking.location:
                lines.append(f"   Location: {booking.location}")

        lines.append("This message contains scheduling information only. Please use the FCA system for any clinical records.")
        return "\n".join(lines)

    @staticmethod
    async def _persist_log(
        db: AsyncIOMotorDatabase,
        log_entry: NotificationLog,
        therapist_id: str
    ) -> NotificationLog:
        await db.notification_log.insert_one(log_entry.model_dump())
        await AuditService.log_activity(
            db,
            action=f"therapist_whatsapp_{'sent' if log_entry.status == 'sent' else 'failed'}",
            client_id=log_entry.client_id,
            booking_id=log_entry.booking_id,
            booking_batch_id=log_entry.booking_batch_id,
            metadata={
                "therapist_id": therapist_id,
                "recipient_masked": _mask_recipient(log_entry.recipient),
                "status": log_entry.status,
                "provider": "meta"
            }
        )
        return log_entry

    @staticmethod
    async def send_booking_whatsapp(
        db: AsyncIOMotorDatabase,
        therapist: Any,
        client: CRMClient,
        bookings: List[Booking],
        booking_batch_id: Optional[str] = None
    ) -> Optional[NotificationLog]:
        if not bookings:
            return None

        target = await TherapistNotificationService._resolve_notification_target(db, therapist)
        therapist_id = str(target.get("id") or getattr(therapist, "id", "unknown"))
        enabled = bool(target.get("whatsapp_notifications_enabled"))
        raw_recipient = target.get("whatsapp_phone")
        recipient = normalize_e164(raw_recipient)

        if not enabled:
            logging.info(
                "Therapist WhatsApp notification skipped: therapist_id=%s enabled=false has_phone=%s",
                therapist_id,
                bool(raw_recipient)
            )
            return None

        summary_text = TherapistNotificationService.build_booking_whatsapp_content(
            therapist, client, bookings
        )
        primary_booking_id = bookings[0].id

        log_entry = NotificationLog(
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            channel="whatsapp",
            recipient=raw_recipient or "None",
            template="therapist_booking_confirmation",
            subject="Therapist Booking Confirmation",
            content_summary=f"Therapist booking notification for {len(bookings)} session(s)",
            status="pending",
            created_at=now_iso()
        )

        if not recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Therapist WhatsApp number must be stored in international E.164 format"
            return await TherapistNotificationService._persist_log(db, log_entry, therapist_id)

        if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_THERAPIST_TEMPLATE_NAME:
            log_entry.status = "failed"
            log_entry.error_message = "Meta therapist notification provider/template is not configured"
            return await TherapistNotificationService._persist_log(db, log_entry, therapist_id)

        first = bookings[0]
        date_str, time_str = _format_booking_datetime(first.starts_at)
        mode = "In-Person" if first.session_mode == "in_person" else "Virtual"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": WHATSAPP_THERAPIST_TEMPLATE_NAME,
                "language": {"code": WHATSAPP_TEMPLATE_LANGUAGE},
                "components": [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "parameter_name": "therapist_name", "text": str(target.get("name") or "Therapist")},
                        {"type": "text", "parameter_name": "client_name", "text": f"{client.first_name} {client.last_name}".strip() or "Client"},
                        {"type": "text", "parameter_name": "client_number", "text": client.client_number},
                        {"type": "text", "parameter_name": "appointment_date", "text": date_str},
                        {"type": "text", "parameter_name": "appointment_time", "text": time_str},
                        {"type": "text", "parameter_name": "session_type", "text": first.session_type.capitalize()},
                        {"type": "text", "parameter_name": "session_mode", "text": mode}
                    ]
                }]
            }
        }
        url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

        def _send_provider():
            return requests.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=15
            )


        try:
            response = await asyncio.to_thread(_send_provider)
            if response.status_code in (200, 201, 202):
                body = response.json() if response.content else {}
                log_entry.status = "sent"
                log_entry.sent_at = now_iso()
                messages = body.get("messages") if isinstance(body, dict) else None
                meta_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
                log_entry.provider_reference = str(
                    meta_id or body.get("message_id") or body.get("id") or "meta-accepted"
                )
                logging.info(
                    "Therapist WhatsApp notification accepted via Meta: therapist_id=%s recipient=%s",
                    therapist_id,
                    _mask_recipient(raw_recipient)
                )
            else:
                log_entry.status = "failed"
                log_entry.error_message = f"Meta therapist notification rejected: {_safe_provider_error(response=response)}"
                logging.warning(
                    "Therapist WhatsApp notification rejected: therapist_id=%s detail=%s",
                    therapist_id,
                    _safe_provider_error(response=response)
                )
        except Exception as exc:
            log_entry.status = "failed"
            log_entry.error_message = f"Therapist WhatsApp delivery error: {_safe_provider_error(exc=exc)}"
            logging.error(
                "Therapist WhatsApp booking confirmation failed for %s",
                _mask_recipient(raw_recipient)
            )

        return await TherapistNotificationService._persist_log(db, log_entry, therapist_id)
