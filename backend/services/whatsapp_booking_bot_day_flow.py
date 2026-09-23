from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from services.whatsapp_booking_bot_service import normalize_sender
from services.whatsapp_booking_bot_fast_slots import MonthlySessionLimitReached, SchedulingAvailabilityError
from services.corporate_entitlement_service import CorporateEntitlementService
from services.booking_service import BookingService
from models import BookingCreateRequest, MultiBookingCreateRequest, SingleBookingSlot


CAT_TZ = ZoneInfo("Africa/Gaborone")


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _day_key(slot: Dict[str, Any]) -> str:
    return _parse_iso(slot["starts_at"]).astimezone(CAT_TZ).date().isoformat()


def _day_label(day_key: str) -> str:
    dt = datetime.fromisoformat(day_key)
    return dt.strftime("%A %d %B %Y")


def _time_label(slot: Dict[str, Any]) -> str:
    return _parse_iso(slot["starts_at"]).astimezone(CAT_TZ).strftime("%H:%M CAT")


def _render_days(day_keys: List[str]) -> str:
    if not day_keys:
        return (
            "No self-service appointment days are available in the next 35 days. "
            "Reply 6 to speak to FCA or MENU to return to the main menu."
        )

    lines = ["Choose an available day:"]
    for index, day_key in enumerate(day_keys, 1):
        lines.append(f"{index}. {_day_label(day_key)}")
    lines.append("\nReply with the day number, or MENU to go back.")
    return "\n".join(lines)


def _unique_time_slots(slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Avoid duplicate clock-time choices when multiple therapists share a slot.

    Routing stays deterministic by retaining the first chronologically sorted slot.
    The final booking service still performs the authoritative conflict check.
    """
    seen = set()
    unique: List[Dict[str, Any]] = []
    for slot in sorted(slots, key=lambda item: item["starts_at"]):
        start_key = _parse_iso(slot["starts_at"]).astimezone(CAT_TZ).strftime("%Y-%m-%dT%H:%M")
        if start_key in seen:
            continue
        seen.add(start_key)
        unique.append(slot)
    return unique


def _corporate_month_series(
    selected: Dict[str, Any],
    slots: List[Dict[str, Any]],
    max_sessions: int,
) -> List[Dict[str, Any]]:
    if max_sessions <= 0:
        return []

    selected_dt = _parse_iso(selected["starts_at"]).astimezone(CAT_TZ)
    month_key = selected_dt.strftime("%Y-%m")
    therapist_id = selected.get("therapist_id")
    preferred_weekday = selected_dt.weekday()
    preferred_minutes = selected_dt.hour * 60 + selected_dt.minute

    def week_key(slot: Dict[str, Any]) -> str:
        local = _parse_iso(slot["starts_at"]).astimezone(CAT_TZ)
        monday = local.date() - __import__("datetime").timedelta(days=local.weekday())
        return monday.isoformat()

    same_month = []
    for slot in slots:
        local = _parse_iso(slot["starts_at"]).astimezone(CAT_TZ)
        if local.strftime("%Y-%m") != month_key:
            continue
        if therapist_id and slot.get("therapist_id") != therapist_id:
            continue
        if local < selected_dt:
            continue
        same_month.append(slot)

    chosen = [selected]
    used_weeks = {week_key(selected)}
    remaining = [slot for slot in same_month if slot.get("starts_at") != selected.get("starts_at")]

    while len(chosen) < max_sessions:
        candidates = [slot for slot in remaining if week_key(slot) not in used_weeks]
        if not candidates:
            break

        def score(slot: Dict[str, Any]):
            local = _parse_iso(slot["starts_at"]).astimezone(CAT_TZ)
            minutes = local.hour * 60 + local.minute
            return (
                0 if local.weekday() == preferred_weekday else 1,
                abs(minutes - preferred_minutes),
                local,
            )

        pick = min(candidates, key=score)
        chosen.append(pick)
        used_weeks.add(week_key(pick))
        remaining = [slot for slot in remaining if slot is not pick]

    return sorted(chosen, key=lambda item: item["starts_at"])


def _render_times(day_key: str, slots: List[Dict[str, Any]]) -> str:
    if not slots:
        return (
            f"No appointment times remain for {_day_label(day_key)}.\n\n"
            "Reply 0 to choose another day or MENU to return to the main menu."
        )

    lines = [_day_label(day_key), "", "Available times:"]
    for index, slot in enumerate(slots, 1):
        lines.append(f"{index}. {_time_label(slot)}")
    lines.append("\n0. Choose another day")
    lines.append("Reply with the time number, or MENU to go back.")
    return "\n".join(lines)


def install_day_first_flow(service_cls) -> None:
    """Install day -> time selection around the existing booking state machine.

    The original service remains authoritative for identity, menu handling, final
    entitlement validation, booking creation, conflict checks, CRM persistence and
    notifications. This wrapper only replaces the appointment-choice interaction.
    """
    if getattr(service_cls, "_day_first_flow_installed", False):
        return

    original_handle = service_cls.handle_inbound

    async def day_first_handle(
        db: AsyncIOMotorDatabase, sender_value: str, text_value: str
    ):
        sender = normalize_sender(sender_value)
        raw_text = str(text_value or "").strip()
        if not sender or not raw_text:
            return await original_handle(db, sender_value, text_value)

        upper_text = raw_text.upper()
        if upper_text in {"MENU", "START", "HELP", "BOT"} or upper_text.startswith("BOOK "):
            return await original_handle(db, sender_value, text_value)

        client_doc, _ = await service_cls._resolve_client(db, sender)
        if not client_doc:
            return await original_handle(db, sender_value, text_value)

        client_id = client_doc["id"]
        first_name = client_doc.get("first_name")
        session = await service_cls._get_session(db, sender)
        if session.get("handoff_active"):
            return await original_handle(db, sender_value, text_value)

        state = session.get("state", "menu")
        context = session.get("context") or {}

        if state == "choose_type":
            type_map = {"1": "individual", "2": "couple", "3": "family"}
            if upper_text not in type_map:
                return "Please reply 1 for Individual, 2 for Couple, or 3 for Family."

            mode = context.get("session_mode")
            if mode not in {"in_person", "virtual"}:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return service_cls.main_menu(first_name)

            try:
                slots = await service_cls._slot_options(db, client_doc, mode, type_map[upper_text])
            except MonthlySessionLimitReached as exc:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return (
                    f"{str(exc)} "
                    "Reply 6 to speak to FCA if you need help with another appointment, "
                    "or MENU to return to the main menu."
                )
            except SchedulingAvailabilityError:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return (
                    "Live appointment availability could not be retrieved from the scheduling calendar right now. "
                    "Reply 6 to speak to FCA or MENU to return to the main menu."
                )

            if not slots:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return (
                    "No self-service appointment days are available in the next 35 days. "
                    "Reply 6 to speak to FCA or MENU to return to the main menu."
                )

            day_keys = sorted({_day_key(slot) for slot in slots})
            new_context = {
                "session_mode": mode,
                "session_type": type_map[upper_text],
                "slots": slots,
                "day_keys": day_keys,
            }
            await service_cls._save_session(
                db, sender, client_id, "choose_day", new_context
            )
            return _render_days(day_keys)

        if state == "choose_day":
            day_keys = context.get("day_keys") or []
            try:
                day_index = int(raw_text) - 1
            except Exception:
                return "Please reply with one of the available day numbers shown."

            if not (0 <= day_index < len(day_keys)):
                return "That day number is not available. Please choose one of the listed days."

            selected_day = day_keys[day_index]
            day_slots = _unique_time_slots(
                [slot for slot in (context.get("slots") or []) if _day_key(slot) == selected_day]
            )
            context["selected_day"] = selected_day
            context["time_slots"] = day_slots
            context.pop("selected_slot", None)
            await service_cls._save_session(
                db, sender, client_id, "choose_time", context
            )
            return _render_times(selected_day, day_slots)

        if state == "choose_time":
            if raw_text == "0":
                context.pop("selected_day", None)
                context.pop("time_slots", None)
                context.pop("selected_slot", None)
                await service_cls._save_session(
                    db, sender, client_id, "choose_day", context
                )
                return _render_days(context.get("day_keys") or [])

            time_slots = context.get("time_slots") or []
            try:
                time_index = int(raw_text) - 1
            except Exception:
                return "Please reply with one of the available time numbers shown, or 0 to choose another day."

            if not (0 <= time_index < len(time_slots)):
                return "That time number is not available. Please choose one of the listed times."

            selected = time_slots[time_index]
            context["selected_slot"] = selected

            if client_doc.get("organisation_id"):
                entitlement = await CorporateEntitlementService.remaining_for_client(
                    db, client_doc, reference=selected["starts_at"]
                )
                remaining = int((entitlement or {}).get("remaining") or 0)
                monthly_series = _corporate_month_series(
                    selected,
                    context.get("slots") or [],
                    max_sessions=min(remaining, 4),
                )
                context["monthly_series"] = monthly_series
                await service_cls._save_session(
                    db, sender, client_id, "confirm_corporate_month", context
                )
                lines = [
                    "Confirm your corporate counselling booking?",
                    "",
                    f"First session: {_day_label(context['selected_day'])} at {_time_label(selected)}",
                    f"Therapist: {selected.get('therapist_name') or 'FCA therapist'}",
                    "",
                    "1. Book this session only",
                ]
                if len(monthly_series) > 1:
                    lines.append(
                        f"2. Book the rest of the month weekly ({len(monthly_series)} sessions total)"
                    )
                lines.extend(["3. Change time", "4. Change day"])
                return "\n".join(lines)

            await service_cls._save_session(
                db, sender, client_id, "confirm_booking", context
            )
            return (
                "Confirm this appointment?\n\n"
                f"{_day_label(context['selected_day'])}\n"
                f"{_time_label(selected)}\n"
                f"{context.get('session_type', 'session').capitalize()} — "
                f"{'Virtual' if context.get('session_mode') == 'virtual' else 'In-Person'}\n"
                f"Therapist: {selected.get('therapist_name') or 'FCA therapist'}\n\n"
                "1. Confirm\n2. Change time\n3. Change day"
            )

        if state == "confirm_corporate_month":
            selected = context.get("selected_slot")
            monthly_series = context.get("monthly_series") or []

            if raw_text == "3":
                context.pop("selected_slot", None)
                context.pop("monthly_series", None)
                await service_cls._save_session(db, sender, client_id, "choose_time", context)
                return _render_times(context.get("selected_day"), context.get("time_slots") or [])

            if raw_text == "4":
                context.pop("selected_day", None)
                context.pop("time_slots", None)
                context.pop("selected_slot", None)
                context.pop("monthly_series", None)
                await service_cls._save_session(db, sender, client_id, "choose_day", context)
                return _render_days(context.get("day_keys") or [])

            if raw_text not in {"1", "2"}:
                return "Reply 1 to book this session, 2 to book weekly for the month, 3 to change time, or 4 to change day."

            if not selected:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return "That booking selection expired. Send BOOK to start again."

            if raw_text == "1" or len(monthly_series) <= 1:
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
                await service_cls._save_session(db, sender, client_id, "menu", {})
                if error or not booking:
                    return (
                        f"That appointment could not be booked: {error or 'the slot is no longer available.'}\n\n"
                        "Send BOOK to see fresh availability."
                    )
                local = _parse_iso(booking.starts_at).astimezone(CAT_TZ)
                return (
                    "Your FCA corporate appointment has been booked successfully. ✅\n"
                    f"{local.strftime('%a %d %b %Y, %H:%M CAT')}\n\n"
                    "Corporate clients may use up to 4 sessions per month, with one session per calendar week. "
                    "Send MENU for more options."
                )

            result, error = await BookingService.create_multi_booking(
                db,
                MultiBookingCreateRequest(
                    client_id=client_id,
                    therapist_id=selected["therapist_id"],
                    session_type=context["session_type"],
                    session_mode=context["session_mode"],
                    slots=[
                        SingleBookingSlot(
                            starts_at=slot["starts_at"],
                            ends_at=slot.get("ends_at"),
                        )
                        for slot in monthly_series
                    ],
                    send_notifications=True,
                    source="whatsapp",
                ),
                actor_id="whatsapp-self-service",
                actor_name="WhatsApp Client Self-Service",
            )
            await service_cls._save_session(db, sender, client_id, "menu", {})
            if error or not result:
                return (
                    f"The monthly booking plan could not be completed: {error or 'availability changed.'}\n\n"
                    "Send BOOK to see fresh availability."
                )

            bookings = result.get("bookings") or []
            lines = [
                f"{len(bookings)} corporate counselling session(s) booked for the month. ✅",
                "One session per calendar week:",
            ]
            for booking in bookings:
                starts_at = booking.starts_at if hasattr(booking, "starts_at") else booking.get("starts_at")
                local = _parse_iso(starts_at).astimezone(CAT_TZ)
                lines.append(f"• {local.strftime('%a %d %b %Y, %H:%M CAT')}")
            if result.get("partial"):
                lines.append("\nSome later slots changed while booking, so only the confirmed appointments above were saved.")
            lines.append("\nSetmore and FCA confirmations will follow. Send MENU for more options.")
            return "\n".join(lines)

        if state == "confirm_booking":
            if raw_text == "2":
                selected_day = context.get("selected_day")
                time_slots = context.get("time_slots") or []
                context.pop("selected_slot", None)
                await service_cls._save_session(
                    db, sender, client_id, "choose_time", context
                )
                return _render_times(selected_day, time_slots)

            if raw_text == "3":
                context.pop("selected_day", None)
                context.pop("time_slots", None)
                context.pop("selected_slot", None)
                await service_cls._save_session(
                    db, sender, client_id, "choose_day", context
                )
                return _render_days(context.get("day_keys") or [])

            return await original_handle(db, sender_value, text_value)

        return await original_handle(db, sender_value, text_value)

    service_cls.handle_inbound = staticmethod(day_first_handle)
    service_cls._day_first_flow_installed = True
