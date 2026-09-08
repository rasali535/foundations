from datetime import datetime, timezone
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from services.whatsapp_booking_bot_service import normalize_sender


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
            "No self-service appointment days are available in the next 7 days. "
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

            slots = await service_cls._slot_options(db, client_doc, mode)
            if not slots:
                await service_cls._save_session(db, sender, client_id, "menu", {})
                return (
                    "No self-service appointment days are available in the next 7 days. "
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
