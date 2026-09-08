import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from models import BookingCreateRequest, now_iso
from services.booking_service import BookingService
from services.therapist_service import TherapistService


CAT_TZ = ZoneInfo("Africa/Gaborone")
DEFAULT_MONTHLY_LIMIT = max(1, int(os.environ.get("FCA_MONTHLY_SESSION_LIMIT", "4")))
BOT_SESSION_TTL_HOURS = max(1, int(os.environ.get("WHATSAPP_BOT_SESSION_TTL_HOURS", "24")))
ACCESS_TOKEN_TTL_DAYS = max(1, int(os.environ.get("WHATSAPP_BOOKING_TOKEN_TTL_DAYS", "7")))
MAX_SLOT_OPTIONS = 6
ENTITLEMENT_STATUSES = ["pending", "confirmed", "completed", "late_cancelled_billable", "no_show"]


def normalize_sender(value: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", str(value or ""))
    if not (8 <= len(digits) <= 15):
        return None
    return f"+{digits}"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _sender_hash(sender: str) -> str:
    return hashlib.sha256(sender.encode("utf-8")).hexdigest()


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_cat(value: str) -> str:
    return _parse_iso(value).astimezone(CAT_TZ).strftime("%a %d %b %Y, %H:%M CAT")


def _month_bounds_utc(reference: datetime) -> Tuple[str, str]:
    local = reference.astimezone(CAT_TZ)
    start = datetime(local.year, local.month, 1, tzinfo=CAT_TZ)
    if local.month == 12:
        end = datetime(local.year + 1, 1, 1, tzinfo=CAT_TZ)
    else:
        end = datetime(local.year, local.month + 1, 1, tzinfo=CAT_TZ)
    return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()


class WhatsAppBookingBotService:
    @staticmethod
    def main_menu(first_name: Optional[str] = None) -> str:
        greeting = f"Hello {first_name}," if first_name else "Hello,"
        return (
            f"{greeting} welcome to FCA WhatsApp Booking.\n\n"
            "1. Book a session\n"
            "2. My appointments\n"
            "3. Reschedule\n"
            "4. Cancel an appointment\n"
            "5. Session balance\n"
            "6. Speak to FCA\n\n"
            "Reply with a number. Send MENU at any time to return here."
        )

    @staticmethod
    async def issue_access_token(db: AsyncIOMotorDatabase, client_id: str, source: str = "intake") -> str:
        raw_token = secrets.token_urlsafe(18)
        created = datetime.now(timezone.utc)
        await db.whatsapp_booking_tokens.insert_one(
            {
                "token_hash": _token_hash(raw_token),
                "client_id": client_id,
                "source": source,
                "created_at": created,
                "expires_at": created + timedelta(days=ACCESS_TOKEN_TTL_DAYS),
                "used_at": None,
            }
        )
        return raw_token

    @staticmethod
    async def _bind_token_to_sender(
        db: AsyncIOMotorDatabase, sender: str, token: str
    ) -> Optional[Dict[str, Any]]:
        token_doc = await db.whatsapp_booking_tokens.find_one(
            {
                "token_hash": _token_hash(token),
                "used_at": None,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
            {"_id": 0},
        )
        if not token_doc:
            return None
        client_doc = await db.crm_clients.find_one(
            {"id": token_doc["client_id"], "status": {"$ne": "archived"}},
            {"_id": 0},
        )
        if not client_doc:
            return None

        now = now_iso()
        await db.crm_clients.update_one(
            {"id": client_doc["id"]},
            {"$set": {"whatsapp_phone": sender, "whatsapp_verified_at": now, "updated_at": now}},
        )
        await db.whatsapp_booking_tokens.update_one(
            {"token_hash": token_doc["token_hash"], "used_at": None},
            {"$set": {"used_at": datetime.now(timezone.utc), "bound_sender_hash": _sender_hash(sender)}},
        )
        client_doc["whatsapp_phone"] = sender
        client_doc["whatsapp_verified_at"] = now
        return client_doc

    @staticmethod
    async def _resolve_client(
        db: AsyncIOMotorDatabase, sender: str, token: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if token:
            bound = await WhatsAppBookingBotService._bind_token_to_sender(db, sender, token)
            return (bound, None) if bound else (None, "invalid_token")

        verified = await db.crm_clients.find_one(
            {"whatsapp_phone": sender, "whatsapp_verified_at": {"$exists": True}},
            {"_id": 0},
        )
        if verified:
            return verified, None

        candidates = await db.crm_clients.find(
            {"phone": sender, "status": {"$ne": "archived"}},
            {"_id": 0},
        ).to_list(3)
        if len(candidates) == 1:
            doc = candidates[0]
            now = now_iso()
            await db.crm_clients.update_one(
                {"id": doc["id"]},
                {"$set": {"whatsapp_phone": sender, "whatsapp_verified_at": now, "updated_at": now}},
            )
            doc["whatsapp_phone"] = sender
            doc["whatsapp_verified_at"] = now
            return doc, None
        if len(candidates) > 1:
            return None, "ambiguous_phone"
        return None, "not_found"

    @staticmethod
    async def _get_session(db: AsyncIOMotorDatabase, sender: str) -> Dict[str, Any]:
        doc = await db.whatsapp_bot_sessions.find_one({"whatsapp_phone": sender}, {"_id": 0})
        if not doc:
            return {"state": "menu", "context": {}, "handoff_active": False}
        try:
            updated = _parse_iso(doc.get("updated_at", now_iso()))
            if datetime.now(timezone.utc) - updated > timedelta(hours=BOT_SESSION_TTL_HOURS):
                return {"state": "menu", "context": {}, "handoff_active": False}
        except Exception:
            pass
        return doc

    @staticmethod
    async def _save_session(
        db: AsyncIOMotorDatabase,
        sender: str,
        client_id: str,
        state: str,
        context: Optional[Dict[str, Any]] = None,
        handoff_active: bool = False,
    ) -> None:
        now = now_iso()
        await db.whatsapp_bot_sessions.update_one(
            {"whatsapp_phone": sender},
            {
                "$set": {
                    "client_id": client_id,
                    "state": state,
                    "context": context or {},
                    "handoff_active": handoff_active,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

    @staticmethod
    async def _monthly_usage(
        db: AsyncIOMotorDatabase, client_doc: Dict[str, Any], reference: datetime
    ) -> Tuple[int, int, int]:
        limit = int(client_doc.get("monthly_session_limit") or DEFAULT_MONTHLY_LIMIT)
        start_iso, end_iso = _month_bounds_utc(reference)
        used = await db.bookings.count_documents(
            {
                "client_id": client_doc["id"],
                "starts_at": {"$gte": start_iso, "$lt": end_iso},
                "status": {"$in": ENTITLEMENT_STATUSES},
            }
        )
        return limit, used, max(limit - used, 0)

    @staticmethod
    async def _slot_options(
        db: AsyncIOMotorDatabase, client_doc: Dict[str, Any], session_mode: str
    ) -> List[Dict[str, Any]]:
        therapists = await TherapistService.list_therapists(
            db, active_only=True, session_mode=session_mode
        )
        if not therapists:
            return []

        today = datetime.now(CAT_TZ).date().isoformat()
        now_utc = datetime.now(timezone.utc)
        candidates: List[Dict[str, Any]] = []
        for therapist in therapists:
            slots = await TherapistService.get_available_slots(
                db, therapist.id, today, days_ahead=30
            )
            for slot in slots:
                if not slot.get("is_available"):
                    continue
                try:
                    start_dt = _parse_iso(slot["starts_at"])
                except Exception:
                    continue
                if start_dt <= now_utc:
                    continue
                _, _, remaining = await WhatsAppBookingBotService._monthly_usage(
                    db, client_doc, start_dt
                )
                if remaining <= 0:
                    continue
                candidates.append(
                    {
                        "therapist_id": therapist.id,
                        "therapist_name": therapist.name,
                        "starts_at": slot["starts_at"],
                        "ends_at": slot["ends_at"],
                    }
                )
        candidates.sort(key=lambda item: item["starts_at"])
        return candidates[:MAX_SLOT_OPTIONS]

    @staticmethod
    def _render_slots(slots: List[Dict[str, Any]]) -> str:
        if not slots:
            return (
                "No self-service appointment slots are available right now. "
                "Reply 6 to speak to FCA or MENU to return to the main menu."
            )
        lines = ["Available appointments:"]
        for index, slot in enumerate(slots, 1):
            lines.append(
                f"{index}. {_format_cat(slot['starts_at'])} — "
                f"{slot.get('therapist_name') or 'FCA therapist'}"
            )
        lines.append("\nReply with the appointment number, or MENU to go back.")
        return "\n".join(lines)

    @staticmethod
    async def _show_appointments(db: AsyncIOMotorDatabase, client_id: str) -> str:
        rows = await db.bookings.find(
            {
                "client_id": client_id,
                "starts_at": {"$gte": datetime.now(timezone.utc).isoformat()},
                "status": {"$in": ["pending", "confirmed"]},
            },
            {"_id": 0},
        ).sort("starts_at", 1).limit(6).to_list(6)

        if not rows:
            return "You have no upcoming FCA appointments.\n\nSend MENU for more options."

        lines = ["Your upcoming FCA appointments:"]
        for index, booking in enumerate(rows, 1):
            lines.append(
                f"{index}. {_format_cat(booking['starts_at'])} — "
                f"{booking.get('session_type', 'session').capitalize()} — "
                f"{'Virtual' if booking.get('session_mode') == 'virtual' else 'In-Person'}"
            )
        lines.append("\nSend MENU for more options.")
        return "\n".join(lines)

    @staticmethod
    async def handle_inbound(
        db: AsyncIOMotorDatabase, sender_value: str, text_value: str
    ) -> Optional[str]:
        sender = normalize_sender(sender_value)
        raw_text = str(text_value or "").strip()
        if not sender or not raw_text:
            return None

        token = None
        token_match = re.match(r"^BOOK\s+([A-Za-z0-9_-]{10,128})$", raw_text, flags=re.IGNORECASE)
        if token_match:
            token = token_match.group(1)

        client_doc, identity_error = await WhatsAppBookingBotService._resolve_client(
            db, sender, token=token
        )
        if not client_doc:
            if identity_error == "invalid_token":
                return "This FCA booking link is invalid or expired. Please contact FCA for a new booking invitation."
            if identity_error == "ambiguous_phone":
                return (
                    "This WhatsApp number matches more than one FCA client record. "
                    "For your privacy, self-service booking has been paused. Please contact FCA."
                )
            return (
                "We could not securely match this WhatsApp number to an FCA client record. "
                "If you completed an intake, use the FCA booking link sent to you or contact FCA administration."
            )

        client_id = client_doc["id"]
        first_name = client_doc.get("first_name")
        text = raw_text.upper()
        session = await WhatsAppBookingBotService._get_session(db, sender)

        if token or text in {"MENU", "START", "HELP", "BOT"}:
            await WhatsAppBookingBotService._save_session(
                db, sender, client_id, "menu", {}, handoff_active=False
            )
            return WhatsAppBookingBotService.main_menu(first_name)

        aliases = {
            "BOOK": "1",
            "BOOK APPOINTMENT": "1",
            "MY BOOKINGS": "2",
            "MY APPOINTMENTS": "2",
            "APPOINTMENTS": "2",
            "RESCHEDULE": "3",
            "CANCEL": "4",
            "BALANCE": "5",
            "SESSION BALANCE": "5",
            "AGENT": "6",
            "HUMAN": "6",
            "FCA": "6",
        }
        text = aliases.get(text, text)

        if session.get("handoff_active"):
            return None

        state = session.get("state", "menu")
        context = session.get("context") or {}

        if state == "menu":
            if text == "1":
                await WhatsAppBookingBotService._save_session(db, sender, client_id, "choose_mode", {})
                return "How would you like your session?\n\n1. In-Person\n2. Virtual\n\nReply 1 or 2."
            if text == "2":
                return await WhatsAppBookingBotService._show_appointments(db, client_id)
            if text == "3":
                return (
                    "Self-service rescheduling is the next booking-bot stage. "
                    "For now, reply 6 to speak to FCA or MENU to continue."
                )
            if text == "4":
                return (
                    "Self-service cancellation is the next booking-bot stage. "
                    "For now, reply 6 to speak to FCA or MENU to continue."
                )
            if text == "5":
                limit, used, remaining = await WhatsAppBookingBotService._monthly_usage(
                    db, client_doc, datetime.now(timezone.utc)
                )
                month_name = datetime.now(CAT_TZ).strftime("%B %Y")
                return (
                    f"{month_name} session balance:\n"
                    f"Used / reserved: {used} of {limit}\n"
                    f"Remaining: {remaining}\n\n"
                    "Timely cancellations do not consume an allocation. "
                    "Late cancellations and no-shows may consume one.\n\nSend MENU for more options."
                )
            if text == "6":
                await db.whatsapp_handoffs.insert_one(
                    {
                        "client_id": client_id,
                        "sender_hash": _sender_hash(sender),
                        "status": "pending",
                        "created_at": now_iso(),
                    }
                )
                await WhatsAppBookingBotService._save_session(
                    db, sender, client_id, "handoff", {}, handoff_active=True
                )
                return (
                    "FCA administration has been notified that you would like assistance. "
                    "A team member will respond here. Send MENU to return to self-service booking."
                )
            return WhatsAppBookingBotService.main_menu(first_name)

        if state == "choose_mode":
            if text not in {"1", "2"}:
                return "Please reply 1 for In-Person or 2 for Virtual."
            session_mode = "in_person" if text == "1" else "virtual"
            await WhatsAppBookingBotService._save_session(
                db, sender, client_id, "choose_type", {"session_mode": session_mode}
            )
            return "Choose session type:\n\n1. Individual\n2. Couple\n3. Family\n\nReply 1, 2 or 3."

        if state == "choose_type":
            type_map = {"1": "individual", "2": "couple", "3": "family"}
            if text not in type_map:
                return "Please reply 1 for Individual, 2 for Couple, or 3 for Family."
            mode = context.get("session_mode")
            if mode not in {"in_person", "virtual"}:
                await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
                return WhatsAppBookingBotService.main_menu(first_name)

            slots = await WhatsAppBookingBotService._slot_options(db, client_doc, mode)
            if not slots:
                await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
                return WhatsAppBookingBotService._render_slots([])

            await WhatsAppBookingBotService._save_session(
                db,
                sender,
                client_id,
                "choose_slot",
                {"session_mode": mode, "session_type": type_map[text], "slots": slots},
            )
            return WhatsAppBookingBotService._render_slots(slots)

        if state == "choose_slot":
            slots = context.get("slots") or []
            try:
                index = int(text) - 1
            except Exception:
                return "Please reply with one of the appointment numbers shown."
            if not (0 <= index < len(slots)):
                return "That appointment number is not available. Please choose one of the listed options."
            selected = slots[index]
            context["selected_slot"] = selected
            await WhatsAppBookingBotService._save_session(
                db, sender, client_id, "confirm_booking", context
            )
            return (
                "Confirm this appointment?\n\n"
                f"{_format_cat(selected['starts_at'])}\n"
                f"{context.get('session_type', 'session').capitalize()} — "
                f"{'Virtual' if context.get('session_mode') == 'virtual' else 'In-Person'}\n"
                f"Therapist: {selected.get('therapist_name') or 'FCA therapist'}\n\n"
                "1. Confirm\n2. Choose another time"
            )

        if state == "confirm_booking":
            if text == "2":
                slots = await WhatsAppBookingBotService._slot_options(
                    db, client_doc, context.get("session_mode")
                )
                context["slots"] = slots
                context.pop("selected_slot", None)
                await WhatsAppBookingBotService._save_session(
                    db, sender, client_id, "choose_slot", context
                )
                return WhatsAppBookingBotService._render_slots(slots)
            if text != "1":
                return "Reply 1 to confirm or 2 to choose another time."

            selected = context.get("selected_slot")
            if not selected:
                await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
                return "That booking selection expired. Send BOOK to start again."

            _, _, remaining = await WhatsAppBookingBotService._monthly_usage(
                db, client_doc, _parse_iso(selected["starts_at"])
            )
            if remaining <= 0:
                await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
                return (
                    "Your session allocation is already fully used or reserved for that month. "
                    "Send BOOK to view other available dates or reply 6 to speak to FCA."
                )

            booking, error = await BookingService.create_booking(
                db,
                BookingCreateRequest(
                    client_id=client_id,
                    therapist_id=selected["therapist_id"],
                    session_type=context["session_type"],
                    session_mode=context["session_mode"],
                    starts_at=selected["starts_at"],
                    ends_at=selected["ends_at"],
                    send_notifications=True,
                    source="whatsapp",
                ),
                actor_id="whatsapp-self-service",
                actor_name="WhatsApp Client Self-Service",
            )
            await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
            if error or not booking:
                return (
                    f"That appointment could not be booked: {error or 'the slot is no longer available.'}\n\n"
                    "Send BOOK to see fresh availability."
                )
            return (
                "Your FCA appointment has been booked successfully. ✅\n"
                f"{_format_cat(booking.starts_at)}\n"
                f"Therapist: {booking.therapist_name or 'FCA therapist'}\n\n"
                "A booking confirmation has also been sent. Send MENU for more options."
            )

        await WhatsAppBookingBotService._save_session(db, sender, client_id, "menu", {})
        return WhatsAppBookingBotService.main_menu(first_name)
