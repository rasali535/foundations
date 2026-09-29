from pathlib import Path

import pytest
from mongomock_motor import AsyncMongoMockClient

from models import BookingCreateRequest, CRMClient
from services.booking_service import BookingService
from services.billing_service import BillingService
from services.corporate_entitlement_service import CorporateEntitlementService
from services.hr_service import HRReportingService
from services.scheduling_service import SchedulingService


@pytest.mark.asyncio
async def test_migrated_client_entitlement_counts_only_attributed_bookings():
    client = AsyncMongoMockClient()
    db = client["historical_org_usage"]

    migrated_client = CRMClient(
        id="client-hist-1",
        client_number="FCA-HIST-1",
        first_name="Historical",
        last_name="Client",
        email="historical@example.com",
        phone="+26771000001",
        organisation_id="org-1",
        organisation_name="Historical Employer",
        organisation_contact_id="contact-1",
        organisation_link_source="historical_migration",
    )

    await db.bookings.insert_many([
        {
            "id": "org-booking",
            "client_id": migrated_client.id,
            "organisation_id": "org-1",
            "starts_at": "2026-09-05T09:00:00+00:00",
            "ends_at": "2026-09-05T10:00:00+00:00",
            "status": "completed",
            "session_type": "individual",
            "session_mode": "in_person",
        },
        {
            "id": "private-booking",
            "client_id": migrated_client.id,
            "organisation_id": None,
            "starts_at": "2026-09-12T09:00:00+00:00",
            "ends_at": "2026-09-12T10:00:00+00:00",
            "status": "completed",
            "session_type": "individual",
            "session_mode": "in_person",
        },
    ])

    used = await CorporateEntitlementService.contact_usage(
        db,
        migrated_client,
        reference="2026-09-20T12:00:00+00:00",
    )
    assert used == 1


@pytest.mark.asyncio
async def test_legacy_corporate_client_keeps_unstamped_booking_fallback():
    client = AsyncMongoMockClient()
    db = client["legacy_org_usage"]

    legacy_client = CRMClient(
        id="client-legacy-1",
        client_number="FCA-LEGACY-1",
        first_name="Legacy",
        last_name="Corporate",
        email="legacy@example.com",
        phone="+26771000002",
        organisation_id="org-legacy",
        organisation_name="Legacy Employer",
    )

    await db.bookings.insert_one({
        "id": "legacy-booking",
        "client_id": legacy_client.id,
        "starts_at": "2026-09-08T09:00:00+00:00",
        "ends_at": "2026-09-08T10:00:00+00:00",
        "status": "completed",
        "session_type": "individual",
        "session_mode": "virtual",
    })

    used = await CorporateEntitlementService.contact_usage(
        db,
        legacy_client,
        reference="2026-09-20T12:00:00+00:00",
    )
    assert used == 1


@pytest.mark.asyncio
async def test_hr_query_excludes_unselected_private_history_for_migrated_client():
    client = AsyncMongoMockClient()
    db = client["historical_hr_query"]

    await db.crm_clients.insert_one({
        "id": "client-hist-report",
        "organisation_id": "org-report",
        "organisation_link_source": "historical_migration",
    })
    await db.bookings.insert_many([
        {
            "id": "selected-org-session",
            "client_id": "client-hist-report",
            "organisation_id": "org-report",
            "starts_at": "2026-08-10T09:00:00+00:00",
        },
        {
            "id": "unselected-private-session",
            "client_id": "client-hist-report",
            "organisation_id": None,
            "starts_at": "2026-08-17T09:00:00+00:00",
        },
    ])

    query = await HRReportingService._organisation_booking_query(db, "org-report")
    rows = await db.bookings.find(query, {"_id": 0, "id": 1}).to_list(20)
    assert {row["id"] for row in rows} == {"selected-org-session"}


@pytest.mark.asyncio
async def test_new_booking_request_inherits_linked_organisation(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["future_org_stamp"]

    await db.crm_clients.insert_one({
        "id": "client-future-org",
        "client_number": "FCA-FUTURE-ORG",
        "first_name": "Future",
        "last_name": "Corporate",
        "email": "future@example.com",
        "phone": "+26771000003",
        "organisation_id": "org-future",
        "organisation_name": "Future Employer",
        "organisation_contact_id": "contact-future",
        "organisation_link_source": "historical_migration",
        "status": "active",
        "tags": [],
    })
    await db.organisation_contacts.insert_one({
        "id": "contact-future",
        "organisation_id": "org-future",
        "email": "future@example.com",
        "email_normalized": "future@example.com",
        "name": "Future Corporate",
        "active": True,
        "base_session_allocation": 4,
        "extra_sessions_approved": 0,
    })

    monkeypatch.setattr(SchedulingService, "provider", staticmethod(lambda: "internal"))

    booking, error = await BookingService.create_booking_request(
        db,
        BookingCreateRequest(
            client_id="client-future-org",
            session_type="individual",
            session_mode="virtual",
            starts_at="2026-10-06T09:00:00+00:00",
            ends_at="2026-10-06T10:00:00+00:00",
            send_notifications=False,
            source="website_intake",
        ),
        actor_id="public_intake",
        actor_name="Website Intake",
    )

    assert error is None
    assert booking.organisation_id == "org-future"
    assert booking.organisation_name == "Future Employer"
    assert booking.organisation_contact_id == "contact-future"
    assert booking.organisation_attribution_source == "current_client_link"


def test_admin_ui_exposes_historical_organisation_date_selection():
    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend" / "src" / "admin" / "pages" / "AdminClientDetail.js").read_text(encoding="utf-8")
    router = (root / "backend" / "routers" / "crm_router.py").read_text(encoding="utf-8")

    assert "Link Historical Organisation Sessions" in source
    assert "Previous booking dates" in source
    assert "selectedHistoricalBookingIds" in source
    assert "/organisation-link" in source
    assert '@crm_router.post("/clients/{client_id}/organisation-link")' in router
    assert '"organisation_attribution_source": "historical_migration"' in router
    assert '"booking_dates": [row.get("starts_at") for row in attributed]' in router


@pytest.mark.asyncio
async def test_historically_attributed_session_is_billable_for_selected_organisation():
    client = AsyncMongoMockClient()
    db = client["historical_org_billing"]

    await db.organisations.insert_one({
        "id": "org-bill-hist",
        "name": "Historical Billing Employer",
        "code": "HIST-BILL",
        "billing_currency": "BWP",
    })
    await db.crm_clients.insert_one({
        "id": "client-bill-hist",
        "organisation_id": "org-bill-hist",
        "organisation_link_source": "historical_migration",
    })
    await db.bookings.insert_many([
        {
            "id": "selected-historical-session",
            "client_id": "client-bill-hist",
            "organisation_id": "org-bill-hist",
            "organisation_attribution_source": "historical_migration",
            "starts_at": "2026-08-11T09:00:00+00:00",
            "ends_at": "2026-08-11T10:00:00+00:00",
            "status": "completed",
            "session_type": "individual",
            "session_mode": "in_person",
        },
        {
            "id": "private-history-not-selected",
            "client_id": "client-bill-hist",
            "organisation_id": None,
            "organisation_attribution_source": None,
            "starts_at": "2026-08-18T09:00:00+00:00",
            "ends_at": "2026-08-18T10:00:00+00:00",
            "status": "completed",
            "session_type": "individual",
            "session_mode": "in_person",
        },
    ])

    eligible = await BillingService.get_uninvoiced_completed_sessions(
        db,
        organisation_id="org-bill-hist",
        start_date="2026-08-01",
        end_date="2026-08-31",
    )

    # Historical-migration clients must bill only the explicitly attributed
    # sessions; their unrelated private history must stay private.
    assert [row["id"] for row in eligible] == ["selected-historical-session"]

    preview = await BillingService.preview_invoice(
        db,
        organisation_id="org-bill-hist",
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert preview.total_sessions == 1
    assert preview.total == 350.0


@pytest.mark.asyncio
async def test_legacy_unstamped_corporate_session_remains_billable():
    client = AsyncMongoMockClient()
    db = client["legacy_org_billing"]

    await db.organisations.insert_one({
        "id": "org-bill-legacy",
        "name": "Legacy Billing Employer",
        "code": "LEG-BILL",
        "billing_currency": "BWP",
    })
    await db.crm_clients.insert_one({
        "id": "client-bill-legacy",
        "organisation_id": "org-bill-legacy",
    })
    await db.bookings.insert_one({
        "id": "legacy-unstamped-session",
        "client_id": "client-bill-legacy",
        "starts_at": "2026-08-09T09:00:00+00:00",
        "ends_at": "2026-08-09T10:00:00+00:00",
        "status": "completed",
        "session_type": "individual",
        "session_mode": "virtual",
    })

    eligible = await BillingService.get_uninvoiced_completed_sessions(
        db,
        organisation_id="org-bill-legacy",
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert [row["id"] for row in eligible] == ["legacy-unstamped-session"]
