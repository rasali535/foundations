import pytest
import pytest_asyncio
import bcrypt
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from decimal import Decimal

from server import app, USERS_DB, RATE_LIMIT_STORE
from models import (
    Therapist, Organisation, OrganisationUser, CRMClient, Booking,
    SESSION_RATES, DEFAULT_CURRENCY
)
from services.billing_service import BillingService

FORBIDDEN_INVOICE_PII = {
    "first_name", "last_name", "client_name", "email", "phone",
    "client_id", "client_number", "booking_id", "therapist_id",
    "therapist_name", "intake_id", "clinical", "triage_level"
}

def scan_for_pii(obj, path=""):
    findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            curr_path = f"{path}.{k}" if path else k
            if k.lower() in FORBIDDEN_INVOICE_PII:
                findings.append(f"Forbidden PII key found: '{curr_path}'")
            findings.extend(scan_for_pii(v, curr_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            findings.extend(scan_for_pii(item, f"{path}[{idx}]"))
    return findings


@pytest_asyncio.fixture
async def billing_test_app():
    RATE_LIMIT_STORE.clear()
    client = AsyncMongoMockClient()
    mock_db = client["test_foundations_db"]
    app.state.db = mock_db

    # Seed system users
    USERS_DB.clear()
    USERS_DB["admin"] = {
        "password_hash": bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "FCA Operations Admin",
        "therapist_id": None
    }
    USERS_DB["therapist1"] = {
        "password_hash": bcrypt.hashpw(b"therapistpass", bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Staff Therapist",
        "therapist_id": "th-01"
    }

    # Seed Organisation A
    org_a = Organisation(
        id="org-test-a",
        name="Corporate Client A",
        code="CORP-A",
        status="active",
        allocated_sessions=100
    )
    await mock_db.organisations.insert_one(org_a.model_dump())

    # Seed Organisation B
    org_b = Organisation(
        id="org-test-b",
        name="Corporate Client B",
        code="CORP-B",
        status="active",
        allocated_sessions=50
    )
    await mock_db.organisations.insert_one(org_b.model_dump())

    # Seed HR User for Org A
    hr_a = OrganisationUser(
        id="hr-user-a",
        organisation_id="org-test-a",
        user_id="hr_user_a",
        email="hr_a@corp-a.com",
        name="HR Director A",
        role="hr_admin",
        password_hash=bcrypt.hashpw(b"hrpassA123!", bcrypt.gensalt()).decode()
    )
    await mock_db.organisation_users.insert_one(hr_a.model_dump())
    USERS_DB["hr_user_a"] = {
        "password_hash": hr_a.password_hash,
        "role": "hr_admin",
        "name": "HR Director A",
        "organisation_id": "org-test-a"
    }

    # Seed HR User for Org B
    hr_b = OrganisationUser(
        id="hr-user-b",
        organisation_id="org-test-b",
        user_id="hr_user_b",
        email="hr_b@corp-b.com",
        name="HR Director B",
        role="hr_admin",
        password_hash=bcrypt.hashpw(b"hrpassB123!", bcrypt.gensalt()).decode()
    )
    await mock_db.organisation_users.insert_one(hr_b.model_dump())
    USERS_DB["hr_user_b"] = {
        "password_hash": hr_b.password_hash,
        "role": "hr_admin",
        "name": "HR Director B",
        "organisation_id": "org-test-b"
    }

    return app, mock_db


@pytest.mark.asyncio
async def test_billing_rates_and_calculation():
    """Verify centralized rates and exact Decimal financial arithmetic: 10 Individual + 3 Couple + 2 Family = BWP 6,500.00"""
    assert SESSION_RATES["individual"] == Decimal("350.00")
    assert SESSION_RATES["couple"] == Decimal("600.00")
    assert SESSION_RATES["family"] == Decimal("600.00")

    counts = {
        "individual": 10,
        "couple": 3,
        "family": 2
    }
    items, subtotal, total, total_sessions = BillingService.calculate_totals(counts)

    assert total_sessions == 15
    assert subtotal == Decimal("6500.00")
    assert total == Decimal("6500.00")

    item_dict = {it.session_type: it for it in items}
    assert item_dict["individual"].quantity == 10
    assert item_dict["individual"].unit_price == 350.0
    assert item_dict["individual"].line_total == 3500.0

    assert item_dict["couple"].quantity == 3
    assert item_dict["couple"].unit_price == 600.0
    assert item_dict["couple"].line_total == 1800.0

    assert item_dict["family"].quantity == 2
    assert item_dict["family"].unit_price == 600.0
    assert item_dict["family"].line_total == 1200.0


@pytest.mark.asyncio
async def test_billable_status_enforcement(billing_test_app):
    """Verify only status = 'completed' sessions are billable; pending, confirmed, cancelled, rescheduled, no_show are excluded."""
    app, db = billing_test_app

    # Create client for Org A
    client_a = CRMClient(
        id="client-a-1",
        first_name="Alice",
        last_name="Smith",
        email="alice@corp-a.com",
        phone="+26771000001",
        client_number="FCA-001",
        organisation_id="org-test-a"
    )
    await db.crm_clients.insert_one(client_a.model_dump())

    # Create bookings with various statuses
    statuses = ["completed", "confirmed", "pending", "cancelled", "rescheduled", "no_show"]
    for idx, st in enumerate(statuses):
        b = Booking(
            id=f"booking-status-{idx}",
            client_id="client-a-1",
            therapist_id="th-01",
            session_type="individual",
            session_mode="in_person",
            starts_at="2026-09-15T10:00:00Z",
            ends_at="2026-09-15T11:00:00Z",
            status=st
        )
        await db.bookings.insert_one(b.model_dump())

    # Query uninvoiced completed sessions
    eligible = await BillingService.get_uninvoiced_completed_sessions(
        db, organisation_id="org-test-a", start_date="2026-09-01", end_date="2026-09-30"
    )

    assert len(eligible) == 1
    assert eligible[0]["id"] == "booking-status-0"
    assert eligible[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_duplicate_billing_prevention(billing_test_app):
    """Verify that generating an invoice links completed bookings, and subsequent generation excludes already-billed sessions."""
    app, db = billing_test_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # Create client for Org A
        client = CRMClient(
            id="client-dup-test",
            first_name="Bob",
            last_name="Test",
            email="bob@corp-a.com",
            phone="+26771000002",
            client_number="FCA-002",
            organisation_id="org-test-a"
        )
        await db.crm_clients.insert_one(client.model_dump())

        # Seed 5 completed sessions
        for i in range(5):
            b = Booking(
                id=f"booking-dup-{i}",
                client_id="client-dup-test",
                therapist_id="th-01",
                session_type="individual",
                session_mode="in_person",
                starts_at=f"2026-09-0{i+1}T10:00:00Z",
                ends_at=f"2026-09-0{i+1}T11:00:00Z",
                status="completed"
            )
            await db.bookings.insert_one(b.model_dump())

        # Preview invoice: should show 5 sessions, BWP 1,750
        prev_resp = await ac.get(
            "/api/invoices/preview?organisation_id=org-test-a&billing_period_start=2026-09-01&billing_period_end=2026-09-30"
        )
        assert prev_resp.status_code == 200
        prev_data = prev_resp.json()
        assert prev_data["total_sessions"] == 5
        assert prev_data["total"] == 1750.0

        # Generate draft invoice
        gen_resp = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30",
            "due_date": "2026-10-15"
        })
        assert gen_resp.status_code == 201
        inv_data = gen_resp.json()["invoice"]
        inv_id = inv_data["id"]
        assert inv_data["invoice_number"].startswith("FCA-INV-2026-")
        assert inv_data["total"] == 1750.0

        # Verify bookings in DB now have active_invoice_id set
        for i in range(5):
            b_doc = await db.bookings.find_one({"id": f"booking-dup-{i}"})
            assert b_doc.get("active_invoice_id") == inv_id

        # Attempt second preview: MUST show 0 sessions remaining
        prev_resp2 = await ac.get(
            "/api/invoices/preview?organisation_id=org-test-a&billing_period_start=2026-09-01&billing_period_end=2026-09-30"
        )
        assert prev_resp2.status_code == 200
        assert prev_resp2.json()["total_sessions"] == 0
        assert prev_resp2.json()["total"] == 0.0

        # Attempt second invoice creation: MUST be rejected with 400 Bad Request
        gen_resp2 = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        assert gen_resp2.status_code == 400
        assert "No eligible completed uninvoiced sessions" in gen_resp2.json()["detail"]


@pytest.mark.asyncio
async def test_organisation_isolation(billing_test_app):
    """Verify Org A invoice strictly includes Org A sessions, and HR user from Org A cannot access Org B invoices."""
    app, db = billing_test_app

    # Create clients for Org A and Org B
    client_a = CRMClient(id="client-iso-a", first_name="A", last_name="A", email="a@a.com", phone="+26771", client_number="FCA-A", organisation_id="org-test-a")
    client_b = CRMClient(id="client-iso-b", first_name="B", last_name="B", email="b@b.com", phone="+26772", client_number="FCA-B", organisation_id="org-test-b")
    await db.crm_clients.insert_many([client_a.model_dump(), client_b.model_dump()])

    # Seed 10 sessions for Org A
    for i in range(10):
        b = Booking(
            id=f"b-org-a-{i}", client_id="client-iso-a", therapist_id="th-01",
            session_type="individual", session_mode="in_person",
            starts_at="2026-09-10T10:00:00Z", ends_at="2026-09-10T11:00:00Z", status="completed"
        )
        await db.bookings.insert_one(b.model_dump())

    # Seed 8 sessions for Org B
    for i in range(8):
        b = Booking(
            id=f"b-org-b-{i}", client_id="client-iso-b", therapist_id="th-01",
            session_type="individual", session_mode="in_person",
            starts_at="2026-09-10T10:00:00Z", ends_at="2026-09-10T11:00:00Z", status="completed"
        )
        await db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Admin creates Invoice for Org A and Org B
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        
        inv_a_resp = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        assert inv_a_resp.status_code == 201
        inv_a_id = inv_a_resp.json()["invoice"]["id"]
        assert inv_a_resp.json()["invoice"]["total_sessions"] == 10
        assert inv_a_resp.json()["invoice"]["total"] == 3500.0

        inv_b_resp = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-b",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        assert inv_b_resp.status_code == 201
        inv_b_id = inv_b_resp.json()["invoice"]["id"]
        assert inv_b_resp.json()["invoice"]["total_sessions"] == 8
        assert inv_b_resp.json()["invoice"]["total"] == 2800.0

        # Issue both invoices
        await ac.post(f"/api/invoices/{inv_a_id}/issue")
        await ac.post(f"/api/invoices/{inv_b_id}/issue")

        # Log out admin
        await ac.post("/api/logout")

        # Log in as HR User A
        hr_login = await ac.post("/api/login", json={"username": "hr_user_a", "password": "hrpassA123!"})
        assert hr_login.status_code == 200

        # HR A lists invoices: MUST only see Org A's invoice
        hr_list = await ac.get("/api/hr/invoices")
        assert hr_list.status_code == 200
        invoices_seen = hr_list.json()
        assert len(invoices_seen) == 1
        assert invoices_seen[0]["id"] == inv_a_id

        # HR A attempts to download Org B's PDF: MUST return 403 Forbidden
        tamper_pdf = await ac.get(f"/api/hr/invoices/{inv_b_id}/pdf")
        assert tamper_pdf.status_code == 403

        # HR A downloads own PDF: MUST return 200 OK
        own_pdf = await ac.get(f"/api/hr/invoices/{inv_a_id}/pdf")
        assert own_pdf.status_code == 200
        assert own_pdf.headers["content-type"] == "application/pdf"
        assert own_pdf.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_privacy_and_zero_pii_on_invoices(billing_test_app):
    """Verify zero client names, client numbers, emails, phone numbers, booking IDs, therapist identities appear on invoice JSON or PDF."""
    app, db = billing_test_app

    # Create client with distinctive sensitive names
    client = CRMClient(
        id="client-pii-check",
        first_name="ConfidentialClientFirst",
        last_name="PrivateClientLast",
        email="confidential@corp-a.com",
        phone="+26779998888",
        client_number="FCA-SECRET-999",
        organisation_id="org-test-a"
    )
    await db.crm_clients.insert_one(client.model_dump())

    booking = Booking(
        id="booking-pii-check",
        client_id="client-pii-check",
        therapist_id="th-01",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-09-12T09:00:00Z",
        ends_at="2026-09-12T10:00:00Z",
        status="completed"
    )
    await db.bookings.insert_one(booking.model_dump())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        
        # Create invoice
        gen_resp = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        assert gen_resp.status_code == 201
        data = gen_resp.json()
        inv_id = data["invoice"]["id"]

        # Scan JSON API response
        findings = scan_for_pii(data)
        assert len(findings) == 0, f"PII found in invoice response: {findings}"

        # Text search against forbidden strings in JSON
        raw_json_text = gen_resp.text
        assert "ConfidentialClientFirst" not in raw_json_text
        assert "PrivateClientLast" not in raw_json_text
        assert "confidential@corp-a.com" not in raw_json_text
        assert "+26779998888" not in raw_json_text
        assert "FCA-SECRET-999" not in raw_json_text
        assert "booking-pii-check" not in raw_json_text

        # Generate & inspect PDF
        pdf_resp = await ac.get(f"/api/invoices/{inv_id}/pdf")
        assert pdf_resp.status_code == 200
        pdf_bytes = pdf_resp.content
        assert pdf_bytes.startswith(b"%PDF-")

        # Scan raw PDF stream for sensitive plain text
        assert b"ConfidentialClientFirst" not in pdf_bytes
        assert b"PrivateClientLast" not in pdf_bytes
        assert b"confidential@corp-a.com" not in pdf_bytes
        assert b"+26779998888" not in pdf_bytes
        assert b"FCA-SECRET-999" not in pdf_bytes
        assert b"booking-pii-check" not in pdf_bytes


@pytest.mark.asyncio
async def test_rbac_access_control(billing_test_app):
    """Verify only super_admin and admin can access admin invoice endpoints; therapist, staff, anonymous are blocked."""
    app, db = billing_test_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Anonymous access: 401 Unauthorized
        anon_resp = await ac.get("/api/invoices")
        assert anon_resp.status_code == 401

        # Therapist access: 403 Forbidden
        await ac.post("/api/login", json={"username": "therapist1", "password": "therapistpass"})
        th_resp = await ac.get("/api/invoices")
        assert th_resp.status_code == 403

        th_gen = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        assert th_gen.status_code == 403
        await ac.post("/api/logout")

        # Admin access: 200 OK
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        admin_resp = await ac.get("/api/invoices")
        assert admin_resp.status_code == 200


@pytest.mark.asyncio
async def test_status_transitions_and_booking_lock(billing_test_app):
    """Verify draft -> issued -> paid transitions; verify issued booking cannot change status; verify cancellation releases bookings."""
    app, db = billing_test_app

    # Create client and 1 completed booking
    client = CRMClient(id="client-lock-test", first_name="Lock", last_name="Test", email="lock@corp-a.com", phone="+26770000000", client_number="FCA-LOCK", organisation_id="org-test-a")
    await db.crm_clients.insert_one(client.model_dump())

    b = Booking(
        id="booking-lock-1", client_id="client-lock-test", therapist_id="th-01",
        session_type="individual", session_mode="in_person",
        starts_at="2026-09-18T10:00:00Z", ends_at="2026-09-18T11:00:00Z", status="completed"
    )
    await db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # 1. Create draft invoice
        gen_resp = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        inv_id = gen_resp.json()["invoice"]["id"]
        assert gen_resp.json()["invoice"]["status"] == "draft"

        # 2. Issue invoice
        issue_resp = await ac.post(f"/api/invoices/{inv_id}/issue")
        assert issue_resp.status_code == 200
        assert issue_resp.json()["status"] == "issued"
        assert issue_resp.json()["issued_at"] is not None

        # 3. Attempt to alter booking status while locked in issued invoice: MUST FAIL
        alter_resp = await ac.post("/api/bookings/booking-lock-1/status", json={"status": "cancelled"})
        assert alter_resp.status_code == 400
        assert "locked in historical issued invoice" in alter_resp.json()["detail"]

        # 4. Mark invoice paid
        pay_resp = await ac.post(f"/api/invoices/{inv_id}/pay")
        assert pay_resp.status_code == 200
        assert pay_resp.json()["status"] == "paid"
        assert pay_resp.json()["paid_at"] is not None

        # 5. Create another draft invoice to test cancellation and booking release
        b2 = Booking(
            id="booking-release-test", client_id="client-lock-test", therapist_id="th-01",
            session_type="couple", session_mode="in_person",
            starts_at="2026-09-20T10:00:00Z", ends_at="2026-09-20T11:00:00Z", status="completed"
        )
        await db.bookings.insert_one(b2.model_dump())

        gen2 = await ac.post("/api/invoices", json={
            "organisation_id": "org-test-a",
            "billing_period_start": "2026-09-01",
            "billing_period_end": "2026-09-30"
        })
        inv2_id = gen2.json()["invoice"]["id"]
        assert gen2.json()["invoice"]["total_sessions"] == 1

        # Check booking has active_invoice_id
        b2_doc = await db.bookings.find_one({"id": "booking-release-test"})
        assert b2_doc.get("active_invoice_id") == inv2_id

        # Cancel inv2
        cancel_resp = await ac.post(f"/api/invoices/{inv2_id}/cancel", json={"reason": "Test billing cancellation"})
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        # Verify b2 active_invoice_id is released
        b2_doc_after = await db.bookings.find_one({"id": "booking-release-test"})
        assert b2_doc_after.get("active_invoice_id") is None

        # Verify b2 can now be reinvoiced
        prev_again = await ac.get("/api/invoices/preview?organisation_id=org-test-a&billing_period_start=2026-09-01&billing_period_end=2026-09-30")
        assert prev_again.status_code == 200
        assert prev_again.json()["total_sessions"] == 1
        assert prev_again.json()["total"] == 600.0
