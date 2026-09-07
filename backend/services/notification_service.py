import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import NotificationLog, Booking, BookingBatch, CRMClient, now_iso
from services.audit_service import AuditService

# Environment configuration
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", "Foundations Counselling & Advisory <noreply@academyfoundations.com>")

META_GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v19.0")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", f"https://graph.facebook.com/{META_GRAPH_API_VERSION}")

def mask_recipient(val: Optional[str]) -> str:
    if not val:
        return "Unknown"
    val = str(val).strip()
    if "@" in val:
        parts = val.split("@", 1)
        name_part = parts[0]
        masked = name_part[0] + "***" + (name_part[-1] if len(name_part) > 1 else "")
        return f"{masked}@{parts[1]}"
    if len(val) >= 7:
        return val[:3] + "****" + val[-2:]
    return "***"

class NotificationService:
    @staticmethod
    def is_email_configured() -> bool:
        return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

    @staticmethod
    def is_whatsapp_configured() -> bool:
        return bool(WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN)

    @staticmethod
    async def get_config_status() -> Dict[str, Any]:
        return {
            "email_configured": NotificationService.is_email_configured(),
            "email_sender": SMTP_FROM,
            "smtp_host": SMTP_HOST or "Unconfigured (Using Local Fallback Logger)",
            "whatsapp_configured": NotificationService.is_whatsapp_configured(),
            "whatsapp_phone_number_id": WHATSAPP_PHONE_NUMBER_ID or "Unconfigured (Using Local Fallback Logger)",
            "operating_timezone": "CAT (UTC+2)"
        }

    # ==================== Email Notification Builder ====================
    @staticmethod
    def build_booking_email_content(
        client: CRMClient,
        bookings: List[Booking],
        is_batch: bool = False
    ) -> Tuple_Content:
        first_b = bookings[0]
        session_type_display = first_b.session_type.capitalize()
        session_mode_display = "In-Person (FCA Clinic)" if first_b.session_mode == "in_person" else "Virtual (Online Video)"
        
        subject = f"Appointment Confirmation: {session_type_display} Counselling with Foundations"
        if is_batch and len(bookings) > 1:
            subject = f"Monthly Multi-Booking Confirmation ({len(bookings)} Sessions) - Foundations Counselling"

        # Build sessions list HTML
        slots_html = ""
        for idx, b in enumerate(bookings, 1):
            date_str = b.starts_at[:10]
            time_str = b.starts_at[11:16] + " UTC"
            slots_html += f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                <p style="margin: 0 0 4px 0; font-weight: 600; color: #1e293b;">Session {idx}: {date_str} at {time_str}</p>
                <p style="margin: 0; font-size: 13px; color: #64748b;">
                    Therapist: <strong>{b.therapist_name or 'Assigned Specialist'}</strong> | 
                    Type: <span style="text-transform: capitalize;">{b.session_type}</span> | 
                    Mode: {session_mode_display}
                </p>
                {f'<p style="margin: 4px 0 0 0; font-size: 12px; color: #0284c7;">Meeting Link: <a href="{b.virtual_meeting_link}">{b.virtual_meeting_link}</a></p>' if b.virtual_meeting_link and b.session_mode == 'virtual' else ''}
                {f'<p style="margin: 4px 0 0 0; font-size: 12px; color: #475569;">Location: {b.location}</p>' if b.location and b.session_mode == 'in_person' else ''}
            </div>
            """

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                <div style="background: #0f172a; padding: 24px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">Foundations Counselling & Advisory</h1>
                    <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 13px;">Pameltex Psychosocial Services</p>
                </div>
                <div style="padding: 24px 28px;">
                    <h2 style="color: #1e293b; font-size: 18px; margin-top: 0;">Dear {client.first_name},</h2>
                    <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                        Your appointment has been successfully scheduled with Foundations Counselling & Advisory. Below are your session details:
                    </p>
                    <div style="margin: 20px 0;">
                        {slots_html}
                    </div>
                    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                        <p style="margin: 0; font-size: 13px; color: #1e40af; line-height: 1.5;">
                            <strong>Confidentiality Notice:</strong> FCA strictly adheres to professional ethics and client privacy. To reschedule or cancel your session, please contact our administrative desk at least 24 hours in advance.
                        </p>
                    </div>
                    <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
                        Warm regards,<br>
                        <strong>Foundations Administration Team</strong><br>
                        Email: info@academyfoundations.com | Phone: +267 71 000 000
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return subject, html_body

    # ==================== Dispatch Engine ====================
    @staticmethod
    async def send_booking_email(
        db: AsyncIOMotorDatabase,
        client: CRMClient,
        bookings: List[Booking],
        booking_batch_id: Optional[str] = None
    ) -> NotificationLog:
        subject, html_body = NotificationService.build_booking_email_content(
            client, bookings, is_batch=bool(booking_batch_id or len(bookings) > 1)
        )
        recipient = client.email
        primary_booking_id = bookings[0].id if bookings else None

        log_entry = NotificationLog(
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            channel="email",
            recipient=recipient,
            template="booking_confirmation",
            subject=subject,
            content_summary=f"{len(bookings)} session(s) booked for {client.first_name} {client.last_name}",
            status="pending",
            created_at=now_iso()
        )

        if not recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Client email address is missing"
            await db.notification_log.insert_one(log_entry.model_dump())
            return log_entry

        if NotificationService.is_email_configured():
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = SMTP_FROM
                msg["To"] = recipient
                msg.attach(MIMEText(html_body, "html"))

                with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(SMTP_FROM, [recipient], msg.as_string())

                log_entry.status = "sent"
                log_entry.sent_at = now_iso()
                log_entry.provider_reference = f"smtp-sent-{now_iso()}"
            except Exception as e:
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                logging.error(f"SMTP Error sending booking confirmation: {e}")
        else:
            # Clean development / fallback logging
            logging.info(f"[MOCK EMAIL DISPATCH] Sent to {mask_recipient(recipient)}: Subject '{subject}'")
            log_entry.status = "sent"
            log_entry.sent_at = now_iso()
            log_entry.provider_reference = "mock-smtp-dev-log"

        await db.notification_log.insert_one(log_entry.model_dump())
        await AuditService.log_activity(
            db,
            action="email_sent" if log_entry.status == "sent" else "email_failed",
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            metadata={"recipient_masked": mask_recipient(recipient), "status": log_entry.status}
        )
        return log_entry

    # ==================== WhatsApp Official Cloud API Engine ====================
    @staticmethod
    async def send_booking_whatsapp(
        db: AsyncIOMotorDatabase,
        client: CRMClient,
        bookings: List[Booking],
        booking_batch_id: Optional[str] = None
    ) -> NotificationLog:
        recipient = client.phone
        primary_booking_id = bookings[0].id if bookings else None
        first_b = bookings[0]
        
        session_mode_str = "In-person at FCA Clinic" if first_b.session_mode == "in_person" else "Virtual Online"
        summary_text = f"Hello {client.first_name}, your FCA Counselling appointment ({first_b.session_type.capitalize()}, {session_mode_str}) has been confirmed for {first_b.starts_at[:10]} at {first_b.starts_at[11:16]} UTC."
        if len(bookings) > 1:
            summary_text = f"Hello {client.first_name}, your {len(bookings)} FCA Counselling appointments have been confirmed. First session: {first_b.starts_at[:10]} at {first_b.starts_at[11:16]} UTC."

        log_entry = NotificationLog(
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            channel="whatsapp",
            recipient=recipient or "None",
            template="whatsapp_booking_confirmation",
            subject="WhatsApp Booking Notification",
            content_summary=summary_text,
            status="pending",
            created_at=now_iso()
        )

        if not recipient:
            log_entry.status = "failed"
            log_entry.error_message = "Client phone number is missing"
            await db.notification_log.insert_one(log_entry.model_dump())
            return log_entry

        if NotificationService.is_whatsapp_configured():
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "text",
                    "text": {"body": summary_text}
                }
                url = f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
                r = requests.post(url, json=payload, headers=headers, timeout=10)
                if r.status_code in [200, 201]:
                    res_json = r.json()
                    log_entry.status = "sent"
                    log_entry.sent_at = now_iso()
                    log_entry.provider_reference = res_json.get("messages", [{}])[0].get("id", "whatsapp-id")
                else:
                    log_entry.status = "failed"
                    log_entry.error_message = f"WhatsApp API HTTP {r.status_code}: {r.text}"
            except Exception as e:
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                logging.error(f"WhatsApp Cloud API Error: {e}")
        else:
            # Clean development / fallback logging
            logging.info(f"[MOCK WHATSAPP DISPATCH] Sent to {mask_recipient(recipient)}: Session notification dispatched")
            log_entry.status = "sent"
            log_entry.sent_at = now_iso()
            log_entry.provider_reference = "mock-whatsapp-dev-log"

        await db.notification_log.insert_one(log_entry.model_dump())
        await AuditService.log_activity(
            db,
            action="whatsapp_sent" if log_entry.status == "sent" else "whatsapp_failed",
            client_id=client.id,
            booking_id=primary_booking_id,
            booking_batch_id=booking_batch_id,
            metadata={"recipient_masked": mask_recipient(recipient), "status": log_entry.status}
        )
        return log_entry

    @staticmethod
    async def list_notifications(
        db: AsyncIOMotorDatabase,
        client_id: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationLog]:
        filter_dict = {}
        if client_id:
            filter_dict["client_id"] = client_id
        cursor = db.notification_log.find(filter_dict, {"_id": 0}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(limit)
        return [NotificationLog(**d) for d in docs]

# Type helper
Tuple_Content = Any
