import os
from typing import Any, Dict, List

from motor.motor_asyncio import AsyncIOMotorDatabase

from services.therapist_service import TherapistService
from services.setmore_service import SetmoreService


class SchedulingService:
    """Single availability gateway used by every FCA booking surface.

    Today the gateway uses FCA's internal calendar. Once Setmore API access is
    provisioned, the Setmore adapter can be enabled here without the website or
    WhatsApp bot implementing separate availability logic.
    """

    @staticmethod
    def provider() -> str:
        return (os.environ.get("FCA_SCHEDULING_PROVIDER") or "internal").strip().lower()

    @staticmethod
    async def get_available_slots(
        db: AsyncIOMotorDatabase,
        therapist_id: str,
        start_date: str,
        days_ahead: int,
        session_type: str = "individual",
        session_mode: str = "virtual",
        funding_scope: str = "private",
        exclude_booking_id: str = None,
    ) -> List[Dict[str, Any]]:
        provider = SchedulingService.provider()
        if provider not in {"internal", "setmore"}:
            raise RuntimeError(f"Unsupported scheduling provider: {provider}")

        if provider == "setmore":
            if not SetmoreService.configured():
                raise RuntimeError("Setmore scheduling is selected but SETMORE_REFRESH_TOKEN is missing.")
            slots = await SetmoreService.available_slots(
                db,
                therapist_id=therapist_id,
                start_date=start_date,
                days_ahead=days_ahead,
                session_type=session_type,
                session_mode=session_mode,
                funding_scope=funding_scope,
            )

        else:
            slots = await TherapistService.get_available_slots(
                db,
                therapist_id=therapist_id,
                start_date_str=start_date,
                days_ahead=days_ahead,
            )
        from services.slot_reservation_service import SlotReservationService
        # Apply local therapist leave even when slots originate from Setmore.
        from datetime import datetime, timezone

        def as_utc(value):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)

        blocks = await db.therapist_blocks.find(
            {"therapist_id": therapist_id}, {"_id": 0, "starts_at": 1, "ends_at": 1}
        ).to_list(1000)
        intervals = [(as_utc(b["starts_at"]), as_utc(b["ends_at"])) for b in blocks]
        for slot in slots:
            if slot.get("is_available") and slot.get("starts_at") and slot.get("ends_at"):
                start, end = as_utc(slot["starts_at"]), as_utc(slot["ends_at"])
                if any(start < blocked_end and end > blocked_start for blocked_start, blocked_end in intervals):
                    slot["is_available"] = False
        return await SlotReservationService.filter_slots(db, slots, exclude_booking_id)
