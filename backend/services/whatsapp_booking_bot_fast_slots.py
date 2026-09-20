import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from services.therapist_service import TherapistService
from services.scheduling_service import SchedulingService
from services.corporate_entitlement_service import CorporateEntitlementService


CAT_TZ = ZoneInfo("Africa/Gaborone")
AVAILABILITY_DAYS = 7
CORPORATE_AVAILABILITY_DAYS = 35
MAX_WEEKLY_SLOTS = 100
ENTITLEMENT_STATUSES = ["pending", "confirmed", "completed", "late_cancelled_billable", "no_show"]


class MonthlySessionLimitReached(RuntimeError):
    """Raised when calendar slots exist but the client has no monthly entitlement left."""



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
    session_type: str = "individual",
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
    logging.warning(
        "WA_SCHED_TRACE stage=therapists mode=%s type=%s count=%s provider=%s",
        session_mode, session_type, len(therapists), SchedulingService.provider()
    )
    if not therapists:
        logging.warning(
            "WA_SCHED_TRACE stage=short_circuit reason=no_therapists mode=%s type=%s",
            session_mode, session_type
        )
        return []

    today = datetime.now(CAT_TZ).date().isoformat()
    now_utc = datetime.now(timezone.utc)

    days_ahead = CORPORATE_AVAILABILITY_DAYS if client_doc.get("organisation_id") else AVAILABILITY_DAYS
    availability_results = await asyncio.gather(
        *(
            SchedulingService.get_available_slots(
                db, therapist.id, today, days_ahead=days_ahead,
                session_mode=session_mode, session_type=session_type
            )
            for therapist in therapists
        ),
        return_exceptions=True,
    )

    candidates: List[Dict[str, Any]] = []
    for therapist, slots in zip(therapists, availability_results):
        if isinstance(slots, Exception):
            logging.error(
                "Scheduling availability failed provider=%s therapist_id=%s mode=%s type=%s error=%s",
                SchedulingService.provider(), therapist.id, session_mode, session_type, str(slots)
            )
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

    logging.warning(
        "WA_SCHED_TRACE stage=candidates mode=%s type=%s count=%s",
        session_mode, session_type, len(candidates)
    )
    if not candidates:
        return []

    # Corporate/EAP clients receive four sessions per calendar month, with no
    # more than one entitlement-consuming session per calendar week.
    if client_doc.get("organisation_id"):
        eligible: List[Dict[str, Any]] = []
        blocked_months = set()
        month_cache: Dict[str, Dict[str, int]] = {}
        week_cache: Dict[str, bool] = {}

        for item in sorted(candidates, key=lambda row: row["starts_at"]):
            starts_at = item["starts_at"]
            month_key = CorporateEntitlementService.month_key(starts_at)
            if month_key not in month_cache:
                month_cache[month_key] = await CorporateEntitlementService.remaining_for_client(
                    db, client_doc, reference=starts_at
                )
            entitlement = month_cache[month_key]
            if entitlement and entitlement["remaining"] <= 0:
                blocked_months.add(month_key)
                continue

            week_start, _ = CorporateEntitlementService.week_bounds_utc(starts_at)
            if week_start not in week_cache:
                week_cache[week_start] = await CorporateEntitlementService.has_weekly_booking(
                    db, client_doc["id"], starts_at
                )
            if week_cache[week_start]:
                continue

            item.pop("_month_key", None)
            eligible.append(item)
            if len(eligible) >= MAX_WEEKLY_SLOTS:
                break

        if not eligible:
            first_entitlement = next(iter(month_cache.values()), None)
            if first_entitlement and first_entitlement["limit"] <= 0:
                raise MonthlySessionLimitReached(
                    "Your corporate email is not currently linked to an active FCA employee roster entry. "
                    "Please contact your organisation or FCA before booking."
                )
            if blocked_months:
                raise MonthlySessionLimitReached(
                    "You have used your corporate counselling allocation for this month. "
                    "Additional sessions require therapist approval."
                )
        return eligible

    candidates.sort(key=lambda item: item["starts_at"])
    month_keys = sorted({item["_month_key"] for item in candidates})
    remaining_results = await asyncio.gather(
        *(_month_remaining(db, client_doc, key) for key in month_keys)
    )
    remaining_by_month = dict(remaining_results)

    eligible: List[Dict[str, Any]] = []
    blocked_months = set()
    for item in candidates:
        month_key = item.pop("_month_key")
        if remaining_by_month.get(month_key, 0) <= 0:
            blocked_months.add(month_key)
            continue
        eligible.append(item)
        if len(eligible) >= MAX_WEEKLY_SLOTS:
            break

    if not eligible and blocked_months:
        logging.warning(
            "WA_SCHED_TRACE stage=entitlement_block client_id=%s blocked_months=%s",
            client_doc.get("id"),
            sorted(blocked_months),
        )
        raise MonthlySessionLimitReached(
            "You have reached your self-service session limit for this month."
        )

    return eligible
