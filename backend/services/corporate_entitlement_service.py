from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from models import now_iso


ENTITLEMENT_STATUSES = ["pending", "confirmed", "completed", "late_cancelled_billable", "no_show"]
DEFAULT_SESSIONS_PER_MEMBER = 4


class CorporateEntitlementService:
    """Corporate roster and session entitlement rules.

    Each active roster member receives four sessions for the organisation's
    contract period. Additional sessions must be explicitly approved and stored
    on that roster member. Corporate pool totals are therefore derived rather
    than manually typed.
    """

    @staticmethod
    def normalize_email(value: Optional[str]) -> str:
        return str(value or "").strip().lower()

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
    async def contact_usage(
        db: AsyncIOMotorDatabase,
        client_id: str,
        organisation_id: str,
    ) -> int:
        org = await db.organisations.find_one({"id": organisation_id}, {"_id": 0})
        query: Dict[str, Any] = {
            "client_id": client_id,
            "status": {"$in": ENTITLEMENT_STATUSES},
        }
        if org and org.get("contract_start") and org.get("contract_end"):
            query["starts_at"] = {
                "$gte": f"{org['contract_start']}T00:00:00",
                "$lte": f"{org['contract_end']}T23:59:59",
            }
        return await db.bookings.count_documents(query)

    @staticmethod
    async def remaining_for_client(
        db: AsyncIOMotorDatabase,
        client: Any,
    ) -> Optional[Dict[str, int]]:
        def value(field: str):
            return client.get(field) if isinstance(client, dict) else getattr(client, field, None)

        organisation_id = value("organisation_id")
        client_id = value("id")
        if not organisation_id or not client_id:
            return None

        contact = await CorporateEntitlementService.get_contact_for_client(db, client)
        if not contact:
            return {
                "base": 0,
                "extra": 0,
                "limit": 0,
                "used": 0,
                "remaining": 0,
            }

        base = int(contact.get("base_session_allocation") or DEFAULT_SESSIONS_PER_MEMBER)
        extra = max(int(contact.get("extra_sessions_approved") or 0), 0)
        limit = max(base + extra, 0)
        used = await CorporateEntitlementService.contact_usage(
            db, str(client_id), str(organisation_id)
        )
        return {
            "base": base,
            "extra": extra,
            "limit": limit,
            "used": used,
            "remaining": max(limit - used, 0),
        }

    @staticmethod
    async def organisation_pool_summary(
        db: AsyncIOMotorDatabase,
        organisation_id: str,
    ) -> Dict[str, int]:
        contacts = await db.organisation_contacts.find(
            {
                "organisation_id": organisation_id,
                "active": True,
                "email_normalized": {"$nin": [None, ""]},
            },
            {"_id": 0, "base_session_allocation": 1, "extra_sessions_approved": 1},
        ).to_list(50000)

        member_count = len(contacts)
        base_sessions = sum(
            int(contact.get("base_session_allocation") or DEFAULT_SESSIONS_PER_MEMBER)
            for contact in contacts
        )
        approved_extra_sessions = sum(
            max(int(contact.get("extra_sessions_approved") or 0), 0)
            for contact in contacts
        )
        return {
            "member_count": member_count,
            "base_sessions": base_sessions,
            "approved_extra_sessions": approved_extra_sessions,
            "allocated_sessions": base_sessions + approved_extra_sessions,
        }
