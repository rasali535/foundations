import pytest
from mongomock_motor import AsyncMongoMockClient

from services.corporate_entitlement_service import CorporateEntitlementService


@pytest.mark.asyncio
async def test_corporate_four_sessions_reset_each_month_and_weekly_limit():
    db = AsyncMongoMockClient()["test_corporate_entitlement"]
    org_id = "org-a"
    client_id = "client-a"

    await db.organisation_contacts.insert_one({
        "id": "roster-a",
        "organisation_id": org_id,
        "name": "Roster Member",
        "email": "member@corp.test",
        "email_normalized": "member@corp.test",
        "active": True,
        "base_session_allocation": 4,
        "extra_sessions_by_month": {},
    })
    await db.crm_clients.insert_one({
        "id": client_id,
        "organisation_id": org_id,
        "organisation_contact_id": "roster-a",
        "email": "member@corp.test",
        "status": "active",
    })
    client = await db.crm_clients.find_one({"id": client_id}, {"_id": 0})

    sept = await CorporateEntitlementService.remaining_for_client(
        db, client, reference="2026-09-01T09:00:00+02:00"
    )
    assert sept["limit"] == 4
    assert sept["remaining"] == 4

    await db.bookings.insert_one({
        "id": "b1",
        "client_id": client_id,
        "starts_at": "2026-09-03T07:00:00+00:00",
        "status": "confirmed",
    })

    ok, reason = await CorporateEntitlementService.validate_slot(
        db, client, "2026-09-04T10:00:00+02:00"
    )
    assert ok is False
    assert "one session per calendar week" in reason

    for idx, starts_at in enumerate(
        [
            "2026-09-10T08:00:00+00:00",
            "2026-09-17T08:00:00+00:00",
            "2026-09-24T08:00:00+00:00",
        ],
        start=2,
    ):
        await db.bookings.insert_one({
            "id": f"b{idx}",
            "client_id": client_id,
            "starts_at": starts_at,
            "status": "confirmed",
        })

    sept_full = await CorporateEntitlementService.remaining_for_client(
        db, client, reference="2026-09-25T09:00:00+02:00"
    )
    assert sept_full["used"] == 4
    assert sept_full["remaining"] == 0

    october = await CorporateEntitlementService.remaining_for_client(
        db, client, reference="2026-10-01T09:00:00+02:00"
    )
    assert october["used"] == 0
    assert october["limit"] == 4
    assert october["remaining"] == 4


@pytest.mark.asyncio
async def test_month_specific_therapist_extra_session_does_not_roll_forward():
    db = AsyncMongoMockClient()["test_corporate_entitlement_extra"]
    await db.organisation_contacts.insert_one({
        "id": "roster-a",
        "organisation_id": "org-a",
        "name": "Roster Member",
        "email": "member@corp.test",
        "email_normalized": "member@corp.test",
        "active": True,
        "base_session_allocation": 4,
        "extra_sessions_by_month": {"2026-09": 1},
    })
    client = {
        "id": "client-a",
        "organisation_id": "org-a",
        "organisation_contact_id": "roster-a",
        "email": "member@corp.test",
    }

    sept = await CorporateEntitlementService.remaining_for_client(
        db, client, reference="2026-09-01T09:00:00+02:00"
    )
    october = await CorporateEntitlementService.remaining_for_client(
        db, client, reference="2026-10-01T09:00:00+02:00"
    )
    assert sept["limit"] == 5
    assert october["limit"] == 4


@pytest.mark.asyncio
async def test_roster_pool_is_monthly_and_isolated_per_corporate():
    db = AsyncMongoMockClient()["test_corporate_pool"]

    await db.organisation_contacts.insert_many([
        {
            "id": "a1",
            "organisation_id": "org-a",
            "email_normalized": "a1@corp.test",
            "active": True,
            "base_session_allocation": 4,
            "extra_sessions_by_month": {},
        },
        {
            "id": "a2",
            "organisation_id": "org-a",
            "email_normalized": "a2@corp.test",
            "active": True,
            "base_session_allocation": 4,
            "extra_sessions_by_month": {"2026-09": 2},
        },
        {
            "id": "b1",
            "organisation_id": "org-b",
            "email_normalized": "b1@corp.test",
            "active": True,
            "base_session_allocation": 4,
            "extra_sessions_by_month": {},
        },
    ])

    pool_a_sept = await CorporateEntitlementService.organisation_pool_summary(
        db, "org-a", reference="2026-09-01T09:00:00+02:00"
    )
    pool_a_oct = await CorporateEntitlementService.organisation_pool_summary(
        db, "org-a", reference="2026-10-01T09:00:00+02:00"
    )
    pool_b_sept = await CorporateEntitlementService.organisation_pool_summary(
        db, "org-b", reference="2026-09-01T09:00:00+02:00"
    )

    assert pool_a_sept["member_count"] == 2
    assert pool_a_sept["allocated_sessions"] == 10
    assert pool_a_oct["allocated_sessions"] == 8
    assert pool_b_sept["member_count"] == 1
    assert pool_b_sept["allocated_sessions"] == 4
