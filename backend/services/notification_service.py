import os
import re
import html
import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Tuple
from zoneinfo import ZoneInfo

import requests
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import NotificationLog, Booking, CRMClient, now_iso
from services.audit_service import AuditService

# ==================== Environment Configuration ====================
# Render Free can make outbound HTTPS requests but SMTP delivery on common mail ports
# is not a reliable production path. HTTPS email delivery is therefore the default.
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "resend").strip().lower()
EMAIL_FROM = (
    os.environ.get("EMAIL_FROM")
    or os.environ.get("RESEND_FROM")
    or os.environ.get("SMTP_FROM")
)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_API_URL = os.environ.get("RESEND_API_URL", "https://api.resend.com/emails")

# Optional SMTP path for paid/local environments.
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM") or EMAIL_FROM

# WhatsApp provider can be explicitly selected as "meta" or "baileys".
# We do not automatically fail over from Meta to Baileys because that can create
# duplicate sends and should never be used to bypass Meta template requirements.
WHATSAPP_PROVIDER = os.environ.get("WHATSAPP_PROVIDER", "meta").strip().lower()
META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v19.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", f"https://graph.facebook.com/{META_GRAPH_API_VERSION}")
WHATSAPP_BOOKING_TEMPLATE_NAME = os.environ.get("WHATSAPP_BOOKING_TEMPLATE_NAME")
WHATSAPP_TEMPLATE_LANGUAGE = os.environ.get("WHATSAPP_TEMPLATE_LANGUAGE", "en")

# Optional Baileys adapter. Baileys runs as a separate Node.js service because it is
# a WhatsApp Web client and requires persistent linked-device credentials.
BAILEYS_SERVICE_URL = os.environ.get("BAILEYS_SERVICE_URL")
BAILEYS_SERVICE_TOKEN = os.environ.get("BAILEYS_SERVICE_TOKEN")

CAT_TZ = ZoneInfo("Africa/Gaborone")


def mask_recipient(val: Optional[str]) -> str:
    if not val:
        return "Unknown"
    val = str(val).strip()
    if "@" in val:
        parts = val.split("@", 1)
        name_part = parts[0]
        masked = (name_part[:1] or "*") + "***" + (name_part[-1:] if len(name_part) > 1 else "")
        return f"{masked}@{parts[1]}"
    digits = re.sub(r"\D", "", val)
    if len(digits) >= 7:
        return digits[:3] + "****" + digits[-2:]
    return "***"


def whatsapp_recipient(val: Optional[str]) -> Optional[str]:
    """Normalize an explicit E.164 phone number without guessing or appending a country code."""
    if not val:
        return None
    raw = str(val).strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+") and 8 <= len(digits) <= 15:
        return digits
    return None


def _cat_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CAT_TZ)


def _format_booking_datetime(value: str) -> Tuple[str, str]:
    dt = _cat_datetime(value)
    return dt.strftime("%a %d %b %Y"), dt.strftime("%H:%M CAT")


def _safe_provider_error(prefix: str, response: Optional[requests.Response] = None, exc: Optional[Exception] = None) -> str:
    if response is not None:
        code = None
        message = None
        try:
            body = response.json()
            err = body.get("error") if isinstance(body, dict) else None
            if isinstance(err, dict):
                code = err.get("code") or err.get("type")
                message = err.get("message")
            elif isinstance(body, dict):
                message = body.get("message") or body.get("error")
        except Exception:
            pass
        detail = f"HTTP {response.status_code}"
        if code:
            detail += f" code={code}"
        if message:
            detail += f" {str(message)[:180]}"
        return f"{prefix}: {detail}"
    if exc is not None:
        return f"{prefix}: {exc.__class__.__name__}"
    return prefix


class NotificationService:
    @staticmethod
    def is_email_configured() -> bool:
        if EMAIL_PROVIDER == "resend":
            return bool(RESEND_API_KEY and EMAIL_FROM)
        if EMAIL_PROVIDER == "smtp":
            return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM)
        return False

    @staticmethod
    def is_whatsapp_configured() -> bool:
        if WHATSAPP_PROVIDER == "meta":
            return bool(
                WHATSAPP_PHONE_NUMBER_ID
                and WHATSAPP_ACCESS_TOKEN
                and WHATSAPP_BOOKING_TEMPLATE_NAME
            )
        if WHATSAPP_PROVIDER == "baileys":
            return bool(BAILEYS_SERVICE_URL and BAILEYS_SERVICE_TOKEN)
        return False

    @staticmethod
    async def get_config_status() -> Dict[str, Any]:
        return {
            "email_provider": EMAIL_PROVIDER,
            "email_configured": NotificationService.is_email_configured(),
            "email_sender_configured": bool(EMAIL_FROM),
            "whatsapp_provider": WHATSAPP_PROVIDER,
            "whatsapp_configured": NotificationService.is_whatsapp_configured(),
            "whatsapp_template_configured": bool(WHATSAPP_BOOKING_TEMPLATE_NAME) if WHATSAPP_PROVIDER == "meta" else None,
            "operating_timezone": "CAT (Africa/Gaborone, UTC+2)",
            "delivery_status_policy": "sent means accepted by a configured provider"
        }

    @staticmethod
    async def _persist_log(db: AsyncIOMotorDatabase, log_entry: NotificationLog) -> NotificationLog:
        await db.notification_log.insert_one(log_entry.model_dump())
        await AuditService.log_activity(
            db,
            action=f"{log_entry.channel}_{'sent' if log_entry.status == 'sent' else 'failed'}",
            client_id=log_entry.client_id,
            booking_id=log_entry.booking_id,
            booking_batch_id=log_entry.booking_batch_id,
            metadata={
                "recipient_masked": mask_recipient(log_entry.recipient),
                "status": log_entry.status,
                "provider": EMAIL_PROVIDER if log_entry.channel == "email" else WHATSAPP_PROVIDER
            }
        )
        return log_entry

    # ==================== Confirmation Content ====================
    @staticmethod
    def build_booking_email_content(
        client: CRMClient,
        bookings: List[Booking],
        is_batch: bool = False
    ) -> Tuple[str, str]:
        first_b = bookings[0]
        session_type_display = first_b.session_type.capitalize()
        subject = f"Appointment Confirmation: {session_type_display} Counselling with Foundations"
        if is_batch and len(bookings) > 1:
            subject = f"Booking Confirmation ({len(bookings)} Sessions) - Foundations Counselling"

        slots_html = ""
        for idx, booking in enumerate(bookings, 1):
            date_str, time_str = _format_booking_datetime(booking.starts_at)
            mode_display = "In-Person" if booking.session_mode == "in_person" else "Virtual"
            therapist_name = html.escape(booking.therapist_name or "Assigned Specialist")
            access_line = ""
            if booking.session_mode == "virtual" and booking.virtual_meeting_link:
                link = html.escape(booking.virtual_meeting_link, quote=True)
                access_line = f'<p style="margin:4px 0 0;font-size:12px;color:#0284c7;">Meeting link: <a href="{link}">{link}</a></p>'
            elif booking.session_mode == "virtual":
                access_line = '<p style="margin:4px 0 0;font-size:12px;color:#475569;">Virtual access details will be provided by FCA administration.</p>'
            elif booking.location:
                access_line = f'<p style="margin:4px 0 0;font-size:12px;color:#475569;">Location: {html.escape(booking.location)}</p>'

            slots_html += f"""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                <p style="margin:0 0 4px;font-weight:600;color:#1e293b;">Session {idx}: {date_str} at {time_str}</p>
                <p style="margin:0;font-size:13px;color:#64748b;">
                    Therapist: <strong>{therapist_name}</strong> | Type: {html.escape(booking.session_type.capitalize())} | Mode: {mode_display}
                </p>
                {access_line}
            </div>
            """

        client_name = html.escape(client.first_name or "Client")
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f1f5f9;margin:0;padding:24px;">
            <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0;">
                <div style="background:#0f172a;padding:24px;text-align:center;">
                    <h1 style="color:#fff;margin:0;font-size:20px;font-weight:700;">Foundations Counselling & Advisory</h1>
                </div>
                <div style="padding:24px 28px;">
                    <h2 style="color:#1e293b;font-size:18px;margin-top:0;">Dear {client_name},</h2>
                    <p style="color:#475569;font-size:14px;line-height:1.6;">Your appointment has been successfully scheduled. Below are your session details:</p>
                    <div style="margin:20px 0;">{slots_html}</div>
                    <div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:12px 16px;margin:20px 0;border-radius:0 8px 8px 0;">
                        <p style="margin:0;font-size:13px;color:#1e40af;line-height:1.5;">
                            <strong>Privacy & scheduling:</strong> Please contact FCA administration at least 6 hours before your appointment if you need to reschedule or cancel. Cancellations within 6 hours may be billable under the FCA cancellation policy.
                        </p>
                    </div>
                    <p style="color:#64748b;font-size:13px;line-height:1.5;margin-bottom:0;">Warm regards,<br><strong>Foundations Administration Team</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        return subject, html_body

    @staticmethod
    def build_booking_whatsapp_content(client: CRMClient, bookings: List[Booking]) -> str:
        first_b = bookings[0]
        date_str, time_str = _format_booking_datetime(first_b.starts_at)
        mode = "In-Person" if first_b.session_mode == "in_person" else "Virtual"
        lines = [
            f"Hello {client.first_name or 'there'}, your Foundations Counselling & Advisory appointment is confirmed.",
            f"Date: {date_str}",
            f"Time: {time_str}",
            f"Session: {first_b.session_type.capitalize()}",
            f"Mode: {mode}",
            f"Therapist: {first_b.therapist_name or 'Assigned Specialist'}"
        ]
        if len(bookings) > 1:
            lines.append(f"Confirmed sessions: {len(bookings)} (details are included in your email confirmation).")
        if first_b.session_mode == "virtual" and first_b.virtual_meeting_link:
            lines.append(f"Meeting link: {first_b.virtual_meeting_link}")
        elif first_b.session_mode == "virtual":
            lines.append("Virtual access details will be provided by FCA administration.")
        elif first_b.location:
            lines.append(f"Location: {first_b.location}")
        lines.append("Please contact FCA at least 6 hours before the appointment if you need to reschedule or cancel.")
        return "\n".join(lines)

    # ==================== Email Dispatch ====================
    @staticmethod
    async def send_booking_email(
        db: AsyncIOMotorDatabase,
        client: CRMClient,
        bookings: List[Booking],
        booking_batch_id: Optional[str] = None
    ) -> NotificationLog:
        primary_booking_id = bookings[0].id if bookings else None
        recipient = getattr(client, "email", None)
        subject = "Booking confirmation"
        html_body = ""
        if bookings:
            subject, html_body = NotificationService.build_booking_email_content(
                client, bookings, is_batch=bool(booking_batch_id or len(bookings) > 1)
            )

        log_entry = NotificationLog(
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            channel="email",
            recipient=recipient or "None",
            template="booking_confirmation",
            subject=subject,
            content_summary=f"Booking confirmation for {len(bookings)} session(s)",
            status="pending",
            created_at=now_iso()
        )

        if not bookings:
            log_entry.status = "failed"
            log_entry.error_message = "No booking supplied for confirmation"
            return await NotificationService._persist_log(db, log_entry)
        if not recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Client email address is missing"
            return await NotificationService._persist_log(db, log_entry)
        if not NotificationService.is_email_configured():
            log_entry.status = "failed"
            log_entry.error_message = f"Email provider '{EMAIL_PROVIDER}' is not configured"
            return await NotificationService._persist_log(db, log_entry)

        try:
            if EMAIL_PROVIDER == "resend":
                def _send_resend():
                    return requests.post(
                        RESEND_API_URL,
                        headers={
                            "Authorization": f"Bearer {RESEND_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "from": EMAIL_FROM,
                            "to": [recipient],
                            "subject": subject,
                            "html": html_body
                        },
                        timeout=15
                    )

                response = await asyncio.to_thread(_send_resend)
                if response.status_code in (200, 201, 202):
                    body = response.json() if response.content else {}
                    log_entry.status = "sent"
                    log_entry.sent_at = now_iso()
                    log_entry.provider_reference = str(body.get("id") or "resend-accepted")
                else:
                    log_entry.status = "failed"
                    log_entry.error_message = _safe_provider_error("Resend delivery rejected", response=response)

            elif EMAIL_PROVIDER == "smtp":
                def _send_smtp():
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = SMTP_FROM
                    msg["To"] = recipient
                    msg.attach(MIMEText(html_body, "html"))
                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                        server.starttls()
                        server.login(SMTP_USER, SMTP_PASSWORD)
                        server.sendmail(SMTP_FROM, [recipient], msg.as_string())

                await asyncio.to_thread(_send_smtp)
                log_entry.status = "sent"
                log_entry.sent_at = now_iso()
                log_entry.provider_reference = "smtp-provider-accepted"
            else:
                log_entry.status = "failed"
                log_entry.error_message = f"Unsupported email provider '{EMAIL_PROVIDER}'"
        except Exception as exc:
            log_entry.status = "failed"
            log_entry.error_message = _safe_provider_error("Email delivery error", exc=exc)
            logging.error("Email booking confirmation failed for %s", mask_recipient(recipient))

        return await NotificationService._persist_log(db, log_entry)

    # ==================== WhatsApp Dispatch ====================
    @staticmethod
    async def send_booking_whatsapp(
        db: AsyncIOMotorDatabase,
        client: CRMClient,
        bookings: List[Booking],
        booking_batch_id: Optional[str] = None
    ) -> NotificationLog:
        primary_booking_id = bookings[0].id if bookings else None
        raw_recipient = getattr(client, "phone", None)
        recipient = whatsapp_recipient(raw_recipient)
        summary_text = NotificationService.build_booking_whatsapp_content(client, bookings) if bookings else ""

        log_entry = NotificationLog(
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            channel="whatsapp",
            recipient=raw_recipient or "None",
            template=WHATSAPP_BOOKING_TEMPLATE_NAME or "booking_confirmation",
            subject="WhatsApp Booking Confirmation",
            content_summary=f"Booking confirmation for {len(bookings)} session(s)",
            status="pending",
            created_at=now_iso()
        )

        if not bookings:
            log_entry.status = "failed"
            log_entry.error_message = "No booking supplied for confirmation"
            return await NotificationService._persist_log(db, log_entry)
        if not raw_recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Client phone number is missing"
            return await NotificationService._persist_log(db, log_entry)
        if not recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Client phone must be stored in international E.164 format"
            return await NotificationService._persist_log(db, log_entry)
        if not NotificationService.is_whatsapp_configured():
            log_entry.status = "failed"
            log_entry.error_message = f"WhatsApp provider '{WHATSAPP_PROVIDER}' is not configured"
            return await NotificationService._persist_log(db, log_entry)

        try:
            if WHATSAPP_PROVIDER == "meta":
                first_b = bookings[0]
                date_str, time_str = _format_booking_datetime(first_b.starts_at)
                mode = "In-Person" if first_b.session_mode == "in_person" else "Virtual"
                if first_b.session_mode == "virtual" and first_b.virtual_meeting_link:
                    access = f"Meeting link: {first_b.virtual_meeting_link}"
                elif first_b.session_mode == "virtual":
                    access = "Virtual access details will be provided by FCA administration."
                elif first_b.location:
                    access = f"Location: {first_b.location}"
                else:
                    access = "FCA administration will provide any additional access details."

                # Approved Meta template body variables, in order:
                # 1 first name, 2 date, 3 time, 4 session type,
                # 5 mode, 6 therapist, 7 access/location details.
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "template",
                    "template": {
                        "name": WHATSAPP_BOOKING_TEMPLATE_NAME,
                        "language": {"code": WHATSAPP_TEMPLATE_LANGUAGE},
                        "components": [{
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": client.first_name or "Client"},
                                {"type": "text", "text": date_str},
                                {"type": "text", "text": time_str},
                                {"type": "text", "text": first_b.session_type.capitalize()},
                                {"type": "text", "text": mode},
                                {"type": "text", "text": first_b.therapist_name or "Assigned Specialist"},
                                {"type": "text", "text": access}
                            ]
                        }]
                    }
                }
                url = f"{WHATSAPP_API_URL.rstrip('/')}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

                def _send_meta():
                    return requests.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        },
                        timeout=15
                    )

                response = await asyncio.to_thread(_send_meta)
                if response.status_code in (200, 201, 202):
                    body = response.json() if response.content else {}
                    messages = body.get("messages") if isinstance(body, dict) else None
                    provider_id = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
                    log_entry.status = "sent"
                    log_entry.sent_at = now_iso()
                    log_entry.provider_reference = provider_id or "meta-accepted"
                else:
                    log_entry.status = "failed"
                    log_entry.error_message = _safe_provider_error("Meta WhatsApp rejected confirmation", response=response)

            elif WHATSAPP_PROVIDER == "baileys":
                url = f"{BAILEYS_SERVICE_URL.rstrip('/')}/send"

                def _send_baileys():
                    return requests.post(
                        url,
                        json={
                            "to": recipient,
                            "text": summary_text,
                            "idempotency_key": primary_booking_id or booking_batch_id
                        },
                        headers={
                            "Authorization": f"Bearer {BAILEYS_SERVICE_TOKEN}",
                            "Content-Type": "application/json"
                        },
                        timeout=15
                    )

                response = await asyncio.to_thread(_send_baileys)
                if response.status_code in (200, 201, 202):
                    body = response.json() if response.content else {}
                    log_entry.status = "sent"
                    log_entry.sent_at = now_iso()
                    log_entry.provider_reference = str(body.get("message_id") or body.get("id") or "baileys-accepted")
                else:
                    log_entry.status = "failed"
                    log_entry.error_message = _safe_provider_error("Baileys service rejected confirmation", response=response)
            else:
                log_entry.status = "failed"
                log_entry.error_message = f"Unsupported WhatsApp provider '{WHATSAPP_PROVIDER}'"

        except Exception as exc:
            log_entry.status = "failed"
            log_entry.error_message = _safe_provider_error("WhatsApp delivery error", exc=exc)
            logging.error("WhatsApp booking confirmation failed for %s", mask_recipient(raw_recipient))

        return await NotificationService._persist_log(db, log_entry)

    @staticmethod
    async def list_notifications(
        db: AsyncIOMotorDatabase,
        client_id: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationLog]:
        filter_dict: Dict[str, Any] = {}
        if client_id:
            filter_dict["client_id"] = client_id
        cursor = db.notification_log.find(filter_dict, {"_id": 0}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(limit)
        return [NotificationLog(**doc) for doc in docs]
