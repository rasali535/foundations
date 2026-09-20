from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from motor.motor_asyncio import AsyncIOMotorDatabase

from models import now_iso


CAT_TZ = ZoneInfo("Africa/Gaborone")
ENTITLEMENT_STATUSES = ["pending", "confirmed", "completed", "late_cancelled_billable", "no_show"]
DEFAULT_SESSIONS_PER_MONTH = 4


class CorporateEntitlementService:
    """Corporate roster and monthly session entitlement rules.

    Each active roster member receives four sessions every calendar month, with
    a maximum of one entitlement-consuming booking per calendar week. Additional
    sessions are month-specific and require therapist/clinical-lead approval.
    """

    @staticmethod
    def normalize_email(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _parse_reference(reference: Optional[Any] = None) -> datetime:
        if reference is None:
            return datetime.now(CAT_TZ)
        if isinstance(reference, datetime):
            dt = reference
        else:
            dt = datetime.fromisoformat(str(reference).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CAT_TZ)

    @staticmethod
    def month_key(reference: Optional[Any] = None) -> str:
        return CorporateEntitlementService._parse_reference(reference).strftime("%Y-%m")

    @staticmethod
    def month_bounds_utc(reference: Optional[Any] = None) -> Tuple[str, str]:
        local = CorporateEntitlementService._parse_reference(reference)
        start = datetime(local.year, local.month, 1, tzinfo=CAT_TZ)
        if local.month == 12:
            end = datetime(local.year + 1, 1, 1, tzinfo=CAT_TZ)
        else:
            end = datetime(local.year, local.month + 1, 1, tzinfo=CAT_TZ)
        return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()

    @staticmethod
    def week_bounds_utc(reference: Any) -> Tuple[str, str]:
        local = CorporateEntitlementService._parse_reference(reference)
        week_start_date = local.date() - timedelta(days=local.weekday())
        start = datetime.combine(week_start_date, datetime.min.time(), tzinfo=CAT_TZ)
        end = start + timedelta(days=7)
        return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()

    @staticmethod
    async def get_contact_for_client(
        db: AsyncIOMotorDatabase,
        client: Any,
    ) -> Optional[Dict[str, Any]]:
        def value(field: str):
            return client.get(field) if isinstance(client, dict) else getattr(client, field, None)

        organisation_id = value("organisation_id")
        if not organisation_id:
            return None

        contact_id = value("organisation_contact_id")
        if contact_id:
            doc = await db.organisation_contacts.find_one(
                {"id": str(contact_id), "organisation_id": organisation_id, "active": True},
                {"_id": 0},
            )
            if doc:
                return doc

        email = CorporateEntitlementService.normalize_email(value("email"))
        if not email:
            return None

        doc = await db.organisation_contacts.find_one(
            {"organisation_id": organisation_id, "email_normalized": email, "active": True},
            {"_id": 0},
        )
        if doc:
            client_id = value("id")
            if client_id:
                await db.crm_clients.update_one(
                    {"id": client_id},
                    {"$set": {"organisation_contact_id": doc["id"], "updated_at": now_iso()}},
                )
        return doc

    @staticmethod
    def _approved_extra_for_month(contact: Dict[str, Any], month_key: str) -> int:
        monthly = contact.get("extra_sessions_by_month") or {}
        if isinstance(monthly, dict):
            return max(int(monthly.get(month_key) or 0), 0)
        return 0

    @staticmethod
    async def contact_usage(
        db: AsyncIOMotorDatabase,
        client_id: str,
        reference: Optional[Any] = None,
    ) -> int:
        start_iso, end_iso = CorporateEntitlementService.month_bounds_utc(reference)
        return await db.bookings.count_documents(
            {
                "client_id": client_id,
                "starts_at": {"$gte": start_iso, "$lt": end_iso},
                "status": {"$in": ENTITLEMENT_STATUSES},
            }
        )

    @staticmethod
    async def has_weekly_booking(
        db: AsyncIOMotorDatabase,
        client_id: str,
        reference: Any,
        exclude_booking_id: Optional[str] = None,
    ) -> bool:
        start_iso, end_iso = CorporateEntitlementService.week_bounds_utc(reference)
        query: Dict[str, Any] = {
            "client_id": client_id,
            "starts_at": {"$gte": start_iso, "$lt": end_iso},
            "status": {"$in": ENTITLEMENT_STATUSES},
        }
        if exclude_booking_id:
            query["id"] = {"$ne": exclude_booking_id}
        return await db.bookings.find_one(query, {"_id": 1}) is not None

    @staticmethod
    async def remaining_for_client(
        db: AsyncIOMotorDatabase,
        client: Any,
        reference: Optional[Any] = None,
    ) -> Optional[Dict[str, int]]:
        def value(field: str):
            return client.get(field) if isinstance(client, dict) else getattr(client, field, None)

        organisation_id = value("organisation_id")
        client_id = value("id")
        if not organisation_id or not client_id:
            return None

        contact = await CorporateEntitlementService.get_contact_for_client(db, client)
        month_key = CorporateEntitlementService.month_key(reference)
        if not contact:
            return {
                "base": 0,
                "extra": 0,
                "limit": 0,
                "used": 0,
                "remaining": 0,
                "month": month_key,
            }

        base = int(contact.get("base_session_allocation") or DEFAULT_SESSIONS_PER_MONTH)
        extra = CorporateEntitlementService._approved_extra_for_month(contact, month_key)
        limit = max(base + extra, 0)
        used = await CorporateEntitlementService.contact_usage(
            db, str(client_id), reference=reference
        )
        return {
            "base": base,
            "extra": extra,
            "limit": limit,
            "used": used,
            "remaining": max(limit - used, 0),
            "month": month_key,
        }

    @staticmethod
    async def validate_slot(
        db: AsyncIOMotorDatabase,
        client: Any,
        starts_at: Any,
        exclude_booking_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        entitlement = await CorporateEntitlementService.remaining_for_client(
            db, client, reference=starts_at
        )
        if entitlement is None:
            return True, None
        if entitlement["limit"] <= 0:
            return False, (
                "Your corporate email is not currently linked to an active FCA employee roster entry. "
                "Please contact your organisation or FCA before booking."
            )
        if entitlement["remaining"] <= 0:
            return False, (
                f"You have used your {entitlement['limit']} allocated corporate session(s) for "
                f"{entitlement['month']}. Additional sessions require therapist approval."
            )

        client_id = client.get("id") if isinstance(client, dict) else getattr(client, "id", None)
        if await CorporateEntitlementService.has_weekly_booking(
            db, str(client_id), starts_at, exclude_booking_id=exclude_booking_id
        ):
            return False, (
                "Corporate counselling allows one session per calendar week. "
                "Please choose a date in another week."
            )
        return True, None

    @staticmethod
    async def organisation_pool_summary(
        db: AsyncIOMotorDatabase,
        organisation_id: str,
        reference: Optional[Any] = None,
    ) -> Dict[str, int]:
        contacts = await db.organisation_contacts.find(
            {
                "organisation_id": organisation_id,
                "active": True,
                "email_normalized": {"$nin": [None, ""]},
            },
            {"_id": 0, "base_session_allocation": 1, "extra_sessions_by_month": 1},
        ).to_list(50000)

        month_key = CorporateEntitlementService.month_key(reference)
        member_count = len(contacts)
        base_sessions = sum(
            int(contact.get("base_session_allocation") or DEFAULT_SESSIONS_PER_MONTH)
            for contact in contacts
        )
        approved_extra_sessions = sum(
            CorporateEntitlementService._approved_extra_for_month(contact, month_key)
            for contact in contacts
        )
        return {
            "member_count": member_count,
            "base_sessions": base_sessions,
            "approved_extra_sessions": approved_extra_sessions,
            "allocated_sessions": base_sessions + approved_extra_sessions,
            "month": month_key,
        }
