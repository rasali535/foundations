import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from services.therapist_service import TherapistService


CAT_TZ = ZoneInfo("Africa/Gaborone")
AVAILABILITY_DAYS = 7
MAX_WEEKLY_SLOTS = 100
ENTITLEMENT_STATUSES = ["pending", "confirmed", "completed", "late_cancelled_billable", "no_show"]


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _month_key(reference: datetime) -> Tuple[int, int]:
    local = reference.astimezone(CAT_TZ)
    return local.year, local.month


def _month_bounds_utc(year: int, month: int) -> Tuple[str, str]:
    start_local = datetime(year, month, 1, tzinfo=CAT_TZ)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, tzinfo=CAT_TZ)
    else:
        end_local = datetime(year, month + 1, 1, tzinfo=CAT_TZ)
    return (
        start_local.astimezone(timezone.utc).isoformat(),
        end_local.astimezone(timezone.utc).isoformat(),
    )


async def _month_remaining(
    db: AsyncIOMotorDatabase,
    client_doc: Dict[str, Any],
    month_key: Tuple[int, int],
) -> Tuple[Tuple[int, int], int]:
    year, month = month_key
    start_iso, end_iso = _month_bounds_utc(year, month)
    limit = int(client_doc.get("monthly_session_limit") or 4)
    used = await db.bookings.count_documents(
        {
            "client_id": client_doc["id"],
            "starts_at": {"$gte": start_iso, "$lt": end_iso},
            "status": {"$in": ENTITLEMENT_STATUSES},
        }
    )
    return month_key, max(limit - used, 0)


async def fast_slot_options(
    db: AsyncIOMotorDatabase,
    client_doc: Dict[str, Any],
    session_mode: str,
) -> List[Dict[str, Any]]:
    """Return all eligible bookable slots from the next seven days.

    WhatsApp now presents available days first and only shows times after a client
    chooses a day. The full weekly slot set is therefore retained in bot state so
    the selected day's times can be rendered without a second expensive calendar
    scan. Therapist availability is still searched week-by-week, while the separate
    FCA entitlement policy remains monthly (default four sessions per month).
    """
    therapists = await TherapistService.list_therapists(
        db, active_only=True, session_mode=session_mode
    )
    if not therapists:
        return []

    today = datetime.now(CAT_TZ).date().isoformat()
    now_utc = datetime.now(timezone.utc)

    availability_results = await asyncio.gather(
        *(
            TherapistService.get_available_slots(
                db, therapist.id, today, days_ahead=AVAILABILITY_DAYS
            )
            for therapist in therapists
        ),
        return_exceptions=True,
    )

    candidates: List[Dict[str, Any]] = []
    for therapist, slots in zip(therapists, availability_results):
        if isinstance(slots, Exception):
            continue
        for slot in slots:
            if not slot.get("is_available"):
                continue
            try:
                start_dt = _parse_iso(slot["starts_at"])
            except Exception:
                continue
            if start_dt <= now_utc:
                continue
            candidates.append(
                {
                    "therapist_id": therapist.id,
                    "therapist_name": therapist.name,
                    "starts_at": slot["starts_at"],
                    "ends_at": slot["ends_at"],
                    "_month_key": _month_key(start_dt),
                }
            )

    if not candidates:
        return []

    candidates.sort(key=lambda item: item["starts_at"])
    month_keys = sorted({item["_month_key"] for item in candidates})
    remaining_results = await asyncio.gather(
        *(_month_remaining(db, client_doc, key) for key in month_keys)
    )
    remaining_by_month = dict(remaining_results)

    eligible: List[Dict[str, Any]] = []
    for item in candidates:
        month_key = item.pop("_month_key")
        if remaining_by_month.get(month_key, 0) <= 0:
            continue
        eligible.append(item)
        if len(eligible) >= MAX_WEEKLY_SLOTS:
            break

    return eligible
