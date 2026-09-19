import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from pymongo.errors import DuplicateKeyError

from services.meta_whatsapp_template_service import MetaWhatsAppTemplateService


CAT_TZ = ZoneInfo("Africa/Gaborone")
POLL_SECONDS = int(os.environ.get("WHATSAPP_REMINDER_POLL_SECONDS", "300"))
WINDOW_MINUTES = int(os.environ.get("WHATSAPP_REMINDER_WINDOW_MINUTES", "7"))


def _format(iso_value: str):
    dt = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(CAT_TZ)
    return local.strftime("%a %d %b %Y"), local.strftime("%H:%M CAT")


class WhatsAppReminderDispatcher:
    """Idempotent booking reminder dispatcher for Meta utility templates."""

    EVENTS = (
        ("booking_reminder_24h", 24 * 60),
        ("virtual_session_link", 3 * 60),
        ("booking_reminder_2h", 2 * 60),
    )

    @staticmethod
    async def _claim(db: Any, booking_id: str, event: str) -> bool:
        key = f"{booking_id}:{event}"
        try:
            await db.whatsapp_dispatch_claims.insert_one(
                {"event_key": key, "booking_id": booking_id, "event": event, "created_at": datetime.now(timezone.utc).isoformat()}
            )
            return True
        except DuplicateKeyError:
            return False

    @staticmethod
    async def _release(db: Any, booking_id: str, event: str) -> None:
        await db.whatsapp_dispatch_claims.delete_one({"event_key": f"{booking_id}:{event}"})

    @staticmethod
    async def dispatch_due(db: Any) -> int:
        if not MetaWhatsAppTemplateService.configured():
            return 0

        now = datetime.now(timezone.utc)
        sent = 0
        for event, lead_minutes in WhatsAppReminderDispatcher.EVENTS:
            target = now + timedelta(minutes=lead_minutes)
            start = (target - timedelta(minutes=WINDOW_MINUTES)).isoformat()
            end = (target + timedelta(minutes=WINDOW_MINUTES)).isoformat()
            query = {
                "status": "confirmed",
                "starts_at": {"$gte": start, "$lte": end},
            }
            if event == "virtual_session_link":
                query.update({
                    "session_mode": "virtual",
                    "virtual_meeting_link": {"$nin": [None, ""]},
                })

            docs = await db.bookings.find(query, {"_id": 0}).to_list(250)
            for booking in docs:
                booking_id = str(booking.get("id") or "")
                client_id = str(booking.get("client_id") or "")
                if not booking_id or not client_id:
                    continue
                if not await WhatsAppReminderDispatcher._claim(db, booking_id, event):
                    continue

                client = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})
                if not client or not client.get("phone"):
                    await WhatsAppReminderDispatcher._release(db, booking_id, event)
                    continue

                date_str, time_str = _format(booking["starts_at"])
                variables = {
                    "client_name": client.get("first_name") or "Client",
                    "appointment_date": date_str,
                    "appointment_time": time_str,
                }
                if event == "booking_reminder_2h":
                    variables = {
                        "client_name": client.get("first_name") or "Client",
                        "appointment_time": time_str,
                    }
                elif event == "virtual_session_link":
                    variables["session_link"] = booking.get("virtual_meeting_link")

                result = await MetaWhatsAppTemplateService.send(
                    db,
                    phone=client["phone"],
                    event=event,
                    variables=variables,
                    client_id=client_id,
                    booking_id=booking_id,
                    booking_batch_id=booking.get("booking_batch_id"),
                )
                if result.status == "sent":
                    sent += 1
                else:
                    # A provider rejection should be retryable on the next poll.
                    await WhatsAppReminderDispatcher._release(db, booking_id, event)
        return sent

    @staticmethod
    async def run_forever(db: Any) -> None:
        while True:
            try:
                await WhatsAppReminderDispatcher.dispatch_due(db)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logging.warning("WhatsApp reminder dispatcher cycle failed: %s", exc.__class__.__name__)
            await asyncio.sleep(max(POLL_SECONDS, 60))
