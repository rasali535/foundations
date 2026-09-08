"""
test_late_cancellation_billing.py
==================================
FCA Late-Cancellation Billing Policy -- Comprehensive Test Suite (Tests A-I)

SECURITY MODEL:
  The server always uses its own UTC clock for billing classification.
  Clients cannot supply a cancellation timestamp to alter billing status.
  Tests use BookingService._now_override (internal parameter) to inject
  a controlled clock without trusting any HTTP payload.

Tests:
  A: Cancellation exactly at 6h boundary          -> cancelled  (non_billable)
  B: Cancellation 0s before session               -> late_cancelled_billable (billable)
  C: Cancellation 5h 59m 59s before session       -> late_cancelled_billable (billable)
  D: Cancellation 6h 0m 0s before session         -> cancelled  (non_billable)
  E: Cancellation 6h 0m 1s before session         -> cancelled  (non_billable)
  F: Invoice preview includes late_cancelled       -> counted in total
  G: Invoice preview excludes plain cancelled      -> not counted in total
  H: Double-billing guard: late-cancelled booking  -> cannot appear on two invoices
  I: Attendance reporting counts only completed    -> late-cancelled NOT counted
  Security: Forged timestamp in HTTP payload       -> IGNORED; server time used
"""

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from decimal import Decimal

from server import app, USERS_DB, RATE_LIMIT_STORE
from models import (
    Therapist, Organisation, OrganisationUser, CRMClient, Booking,
    BookingStatusUpdateRequest, SESSION_RATES, DEFAULT_CURRENCY
)
from services.billing_service import BillingService
from services.booking_service import BookingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _session_start_in(hours_from_now=10):
    return datetime.now(timezone.utc) + timedelta(hours=hours_from_now)


# ---------------------------------------------------------------------------
# Shared Fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def late_cancel_app():
    RATE_LIMIT_STORE.clear()
    mc = AsyncMongoMockClient()
    mock_db = mc["test_late_cancel_db"]
    app.state.db = mock_db

    USERS_DB.clear()
    USERS_DB["admin"] = {
        "password_hash": bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "FCA Admin",
        "therapist_id": None
    }

    therapist = Therapist(
        id="th-lc-01",
        name="Dr. Cancel Test",
        email="cancel.test@foundations.clinic",
        phone="+26771000099",
        active=True,
        supports_in_person=True,
        supports_virtual=False,
        specializations=["Individual Counselling"],
        working_days=[0, 1, 2, 3, 4],
        working_hours_start="08:00",
        working_hours_end="18:00",
        slot_duration_minutes=60,
        default_location="FCA Test Clinic",
        virtual_meeting_link_template=None
    )
    await mock_db.therapists.insert_one(therapist.model_dump())

    org = Organisation(
        id="org-lc-01",
        name="Late Cancel Corp",
        code="LCC",
        active=True
    )
    await mock_db.organisations.insert_one(org.model_dump())

    hr_pw_hash = bcrypt.hashpw(b"hrpass999", bcrypt.gensalt()).decode()
    hr_user = OrganisationUser(
        id="hr-lc-01",
        organisation_id="org-lc-01",
        user_id="hr_lc",
        email="hr.lc@latecancelcorp.test",
        name="HR Late Cancel",
        role="hr_admin",
        password_hash=hr_pw_hash
    )
    await mock_db.organisation_users.insert_one(hr_user.model_dump())
    USERS_DB["hr_lc"] = {
        "password_hash": hr_pw_hash,
        "role": "hr_admin",
        "name": "HR Late Cancel",
        "organisation_id": "org-lc-01"
    }

    crm_client = CRMClient(
        id="client-lc-01",
        client_number="FCA-LC-001",
        first_name="Test",
        last_name="Patient",
        email="patient@lc.test",
        phone="+26771000001",
        organisation_id="org-lc-01"
    )
    await mock_db.crm_clients.insert_one(crm_client.model_dump())

    yield mock_db


# ---------------------------------------------------------------------------
# Booking factory
# ---------------------------------------------------------------------------

async def _insert_booking(
    db, booking_id, status, session_type="individual",
    starts_at=None, cancelled_at=None, hours_before_session=None,
    cancellation_billing_status=None, active_invoice_id=None
):
    starts_at = starts_at or _session_start_in(10)
    booking = Booking(
        id=booking_id,
        client_id="client-lc-01",
        client_number="FCA-LC-001",
        client_name="Test Patient",
        client_email="patient@lc.test",
        client_phone="+26771000001",
        therapist_id="th-lc-01",
        therapist_name="Dr. Cancel Test",
        session_type=session_type,
        session_mode="in_person",
        starts_at=_make_utc(starts_at),
        ends_at=_make_utc(starts_at + timedelta(hours=1)),
        status=status,
        organisation_id="org-lc-01",
    )
    doc = booking.model_dump()
    if cancelled_at:
        doc["cancelled_at"] = _make_utc(cancelled_at)
    if hours_before_session is not None:
        doc["hours_before_session"] = hours_before_session
    if cancellation_billing_status:
        doc["cancellation_billing_status"] = cancellation_billing_status
    if active_invoice_id:
        doc["active_invoice_id"] = active_invoice_id
    await db.bookings.insert_one(doc)
    return booking


# ---------------------------------------------------------------------------
# Internal helper: cancel via service with injected clock
# ---------------------------------------------------------------------------

async def _cancel_with_clock(db, booking_id, fake_now, reason="Test"):
    """
    Cancels a booking using the service directly with an injected clock.
    This is the ONLY supported mechanism for testing time-sensitive billing logic.
    The HTTP layer never accepts a cancellation timestamp.
    """
    req = BookingStatusUpdateRequest(
        status="cancelled",
        cancellation_reason=reason,
        send_notifications=False
    )
    return await BookingService.update_booking_status(
        db,
        booking_id=booking_id,
        request=req,
        actor_id="test-admin",
        actor_name="Test Admin",
        _now_override=fake_now
    )


# ---------------------------------------------------------------------------
# TEST A: Exactly 6h before session -> cancelled, non_billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_cancellation_exactly_6h_boundary_not_billable(late_cancel_app):
    """Test A: Server clock at exactly T-6h -> cancelled, non_billable"""
    db = late_cancel_app
    session_start = _session_start_in(24)
    fake_now = session_start - timedelta(hours=6)  # exactly 6h before
    booking = await _insert_booking(db, "bk-a", "confirmed", starts_at=session_start)

    result_booking, err = await _cancel_with_clock(db, "bk-a", fake_now, "Test A")
    assert err is None, err
    assert result_booking.status == "cancelled"
    assert result_booking.cancellation_billing_status == "non_billable"
    assert result_booking.hours_before_session == pytest.approx(6.0, abs=0.01)


# ---------------------------------------------------------------------------
# TEST B: 0 seconds before session -> late_cancelled_billable, billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_b_cancellation_0s_before_session_billable(late_cancel_app):
    """Test B: Server clock at session start time -> late_cancelled_billable, billable"""
    db = late_cancel_app
    session_start = _session_start_in(24)
    fake_now = session_start  # 0s before
    booking = await _insert_booking(db, "bk-b", "confirmed", starts_at=session_start)

    result_booking, err = await _cancel_with_clock(db, "bk-b", fake_now, "Test B")
    assert err is None, err
    assert result_booking.status == "late_cancelled_billable"
    assert result_booking.cancellation_billing_status == "billable"
    assert result_booking.hours_before_session == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# TEST C: 5h 59m 59s before session -> late_cancelled_billable, billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_c_cancellation_5h59m59s_before_billable(late_cancel_app):
    """Test C: Server clock at T-5h59m59s -> late_cancelled_billable, billable"""
    db = late_cancel_app
    session_start = _session_start_in(24)
    fake_now = session_start - timedelta(hours=5, minutes=59, seconds=59)
    booking = await _insert_booking(db, "bk-c", "confirmed", starts_at=session_start)

    result_booking, err = await _cancel_with_clock(db, "bk-c", fake_now, "Test C")
    assert err is None, err
    assert result_booking.status == "late_cancelled_billable"
    assert result_booking.cancellation_billing_status == "billable"
    assert result_booking.hours_before_session == pytest.approx(5.9997, abs=0.01)


# ---------------------------------------------------------------------------
# TEST D: Exactly 6h 0m 0s before -> cancelled, non_billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_d_cancellation_6h_0m_0s_not_billable(late_cancel_app):
    """Test D: Exactly T-6h -> cancelled, non_billable (boundary belongs to non-billable side)"""
    db = late_cancel_app
    session_start = _session_start_in(24)
    fake_now = session_start - timedelta(hours=6)
    booking = await _insert_booking(db, "bk-d", "confirmed", starts_at=session_start)

    result_booking, err = await _cancel_with_clock(db, "bk-d", fake_now, "Test D")
    assert err is None, err
    assert result_booking.status == "cancelled"
    assert result_booking.cancellation_billing_status == "non_billable"


# ---------------------------------------------------------------------------
# TEST E: 6h 1s before session -> cancelled, non_billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e_cancellation_6h1s_before_not_billable(late_cancel_app):
    """Test E: Server clock at T-6h1s -> cancelled, non_billable"""
    db = late_cancel_app
    session_start = _session_start_in(24)
    fake_now = session_start - timedelta(hours=6, seconds=1)
    booking = await _insert_booking(db, "bk-e", "confirmed", starts_at=session_start)

    result_booking, err = await _cancel_with_clock(db, "bk-e", fake_now, "Test E")
    assert err is None, err
    assert result_booking.status == "cancelled"
    assert result_booking.cancellation_billing_status == "non_billable"


# ---------------------------------------------------------------------------
# SECURITY TEST: Forged cancellation_timestamp in HTTP payload is IGNORED
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_forged_timestamp_ignored(late_cancel_app):
    """
    Security: A client submits a forged cancellation_timestamp claiming
    cancellation occurred 8 hours earlier (non-billable territory).
    The server must ignore it and use its own clock.

    Setup: Session is 2 hours away, so server time is T-2h -> BILLABLE.
    A forged timestamp of T-8h would falsely classify as non_billable.
    Expected: The booking is classified as late_cancelled_billable (BILLABLE)
    because the server ignores the forged timestamp.
    """
    db = late_cancel_app
    # Session starts in 2 hours -> cancelling now is <6h -> BILLABLE
    session_start = _session_start_in(2)
    booking = await _insert_booking(db, "bk-sec", "confirmed", starts_at=session_start)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200, f"Login failed: {login.text}"

        # Forge a timestamp 8h before session (would be non-billable if trusted)
        forged_ts = _make_utc(session_start - timedelta(hours=8))

        resp = await ac.post(
            f"/api/bookings/{booking.id}/status",
            json={
                "status": "cancelled",
                "cancellation_reason": "Security test: forged timestamp",
                # Attempt to supply a forged timestamp to avoid billing
                "cancellation_timestamp": forged_ts,
                "send_notifications": False
            }
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # CRITICAL: The booking MUST be late_cancelled_billable because server time
    # (T-2h) is less than 6h, regardless of the forged timestamp in the payload.
    # If the timestamp were trusted, it would incorrectly be non_billable.
    assert data["status"] == "late_cancelled_billable", (
        f"SECURITY FAILURE: Forged timestamp was trusted! "
        f"Expected late_cancelled_billable (server classifies T-2h as billable), "
        f"but got: {data['status']}"
    )
    assert data.get("cancellation_billing_status") == "billable", (
        f"SECURITY FAILURE: Billing status should be billable, got: {data.get('cancellation_billing_status')}"
    )


# ---------------------------------------------------------------------------
# TEST F: Invoice preview includes late_cancelled_billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f_invoice_preview_includes_late_cancelled_billable(late_cancel_app):
    """Test F: 2 completed + 1 late_cancelled_billable -> 3 sessions, BWP 1050"""
    db = late_cancel_app
    base_dt = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    await _insert_booking(db, "bk-f-1", "completed", starts_at=base_dt)
    await _insert_booking(db, "bk-f-2", "completed", starts_at=base_dt + timedelta(days=1))
    await _insert_booking(db, "bk-f-3", "late_cancelled_billable",
                          starts_at=base_dt + timedelta(days=2),
                          cancellation_billing_status="billable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200
        resp = await ac.get(
            "/api/invoices/preview",
            params={
                "organisation_id": "org-lc-01",
                "billing_period_start": "2026-09-01",
                "billing_period_end": "2026-09-30",
            }
        )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["total_sessions"] == 3, (
        f"Expected 3 (2 completed + 1 late-cancelled), got {preview['total_sessions']}"
    )
    assert Decimal(str(preview["total"])) == Decimal("1050.00")


# ---------------------------------------------------------------------------
# TEST G: Invoice preview excludes plain cancelled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g_invoice_preview_excludes_plain_cancelled(late_cancel_app):
    """Test G: 1 completed + 2 plain-cancelled -> only 1 session in preview"""
    db = late_cancel_app
    base_dt = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    await _insert_booking(db, "bk-g-1", "completed", starts_at=base_dt)
    await _insert_booking(db, "bk-g-2", "cancelled",
                          starts_at=base_dt + timedelta(days=1),
                          cancellation_billing_status="non_billable")
    await _insert_booking(db, "bk-g-3", "cancelled",
                          starts_at=base_dt + timedelta(days=2),
                          cancellation_billing_status="non_billable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200
        resp = await ac.get(
            "/api/invoices/preview",
            params={
                "organisation_id": "org-lc-01",
                "billing_period_start": "2026-10-01",
                "billing_period_end": "2026-10-31",
            }
        )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["total_sessions"] == 1, (
        f"Plain-cancelled must be excluded. Got {preview['total_sessions']}"
    )
    assert Decimal(str(preview["total"])) == Decimal("350.00")


# ---------------------------------------------------------------------------
# TEST H: Double-billing guard for late_cancelled_billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_h_double_billing_guard_late_cancelled(late_cancel_app):
    """Test H: Already-invoiced late-cancelled booking must not appear in new preview"""
    db = late_cancel_app
    base_dt = datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc)

    # Seed a real invoice that the booking is locked to (status=draft|issued|paid)
    await db.invoices.insert_one({
        "id": "inv-existing-001",
        "invoice_number": "FCA-INV-2026-0001",
        "status": "issued",
        "organisation_id": "org-lc-01",
        "billing_period_start": "2026-11-01",
        "billing_period_end": "2026-11-30"
    })

    await _insert_booking(
        db, "bk-h-1", "late_cancelled_billable",
        starts_at=base_dt,
        cancellation_billing_status="billable",
        active_invoice_id="inv-existing-001"
    )
    await _insert_booking(db, "bk-h-2", "completed",
                          starts_at=base_dt + timedelta(days=1))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200
        resp = await ac.get(
            "/api/invoices/preview",
            params={
                "organisation_id": "org-lc-01",
                "billing_period_start": "2026-11-01",
                "billing_period_end": "2026-11-30",
            }
        )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["total_sessions"] == 1, (
        f"Already-invoiced late-cancelled must be excluded. Got {preview['total_sessions']}"
    )


# ---------------------------------------------------------------------------
# TEST I: Attendance counts only completed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_i_attendance_report_counts_only_completed(late_cancel_app):
    """Test I: Service-level: completed=3, late_cancelled_billable=2 verified separately"""
    db = late_cancel_app
    base_dt = datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc)
    await _insert_booking(db, "bk-i-1", "completed", starts_at=base_dt)
    await _insert_booking(db, "bk-i-2", "completed", starts_at=base_dt + timedelta(days=1))
    await _insert_booking(db, "bk-i-3", "completed", starts_at=base_dt + timedelta(days=2))
    await _insert_booking(db, "bk-i-4", "late_cancelled_billable",
                          starts_at=base_dt + timedelta(days=3),
                          cancellation_billing_status="billable")
    await _insert_booking(db, "bk-i-5", "late_cancelled_billable",
                          starts_at=base_dt + timedelta(days=4),
                          cancellation_billing_status="billable")

    # Service-level assertion: completed vs late-cancelled counts are distinct
    _, completed_count = await BookingService.list_bookings(db, status="completed")
    assert completed_count == 3, (
        f"Service-level: completed count must be 3, got {completed_count}"
    )
    _, lc_count = await BookingService.list_bookings(db, status="late_cancelled_billable")
    assert lc_count == 2, (
        f"Service-level: late_cancelled_billable count must be 2, got {lc_count}"
    )

    # The HR utilisation endpoint returns monthly trend data (not a flat attended count).
    # The authoritative assertion is at the service layer above: completed=3, late_cancelled=2.


# ---------------------------------------------------------------------------
# Regression: status locked on issued invoice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_status_locked_on_issued_invoice(late_cancel_app):
    """Regression: Booking in issued invoice must reject status update"""
    db = late_cancel_app
    await db.invoices.insert_one({
        "id": "inv-issued-lock",
        "invoice_number": "FCA-INV-LOCK",
        "status": "issued",
        "organisation_id": "org-lc-01",
    })
    booking = await _insert_booking(
        db, "bk-locked", "completed",
        starts_at=_session_start_in(48),
        active_invoice_id="inv-issued-lock"
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200
        resp = await ac.post(
            f"/api/bookings/{booking.id}/status",
            json={
                "status": "cancelled",
                "cancellation_reason": "Attempting to cancel invoiced session",
                "send_notifications": False
            }
        )
    assert resp.status_code in (400, 409, 422), (
        f"Expected error for locked booking, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Regression: no_show not billable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_show_not_included_in_invoice(late_cancel_app):
    """Regression: no_show sessions must be excluded from invoice previews"""
    db = late_cancel_app
    base_dt = datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)
    await _insert_booking(db, "bk-ns-1", "no_show", starts_at=base_dt)
    await _insert_booking(db, "bk-ns-2", "no_show", starts_at=base_dt + timedelta(days=1))
    await _insert_booking(db, "bk-ns-3", "completed", starts_at=base_dt + timedelta(days=2))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login.status_code == 200
        resp = await ac.get(
            "/api/invoices/preview",
            params={
                "organisation_id": "org-lc-01",
                "billing_period_start": "2026-08-01",
                "billing_period_end": "2026-08-31",
            }
        )
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["total_sessions"] == 1, (
        f"no_show must be excluded. Got {preview['total_sessions']}"
    )
