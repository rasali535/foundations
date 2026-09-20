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
    ) -> List[Dict[str, Any]]:
        provider = SchedulingService.provider()
        if provider not in {"internal", "setmore"}:
            raise RuntimeError(f"Unsupported scheduling provider: {provider}")

        if provider == "setmore":
            if not SetmoreService.configured():
                raise RuntimeError("Setmore scheduling is selected but SETMORE_REFRESH_TOKEN is missing.")
            return await SetmoreService.available_slots(
                db,
                therapist_id=therapist_id,
                start_date=start_date,
                days_ahead=days_ahead,
                session_type=session_type,
                session_mode=session_mode,
            )

        return await TherapistService.get_available_slots(
            db,
            therapist_id=therapist_id,
            start_date_str=start_date,
            days_ahead=days_ahead,
        )
