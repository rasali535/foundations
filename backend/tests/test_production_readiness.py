import pytest
import pytest_asyncio
import asyncio
import os
import bcrypt
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from server import app, USERS_DB, bootstrap_super_admin
from services.crm_service import CRMService, normalize_email, normalize_phone
from services.intake_service import IntakeService
from services.therapist_service import TherapistService, DEFAULT_THERAPISTS
from services.booking_service import BookingService
from services.notification_service import NotificationService
from models import (
    BookingCreateRequest, MultiBookingCreateRequest, SingleBookingSlot,
    BookingRescheduleRequest, BookingStatusUpdateRequest,
    CRMNoteCreate, TherapistCreate, TherapistBlockCreate, Therapist
)

TEST_THERAPIST_IN_PERSON = {
    "id": "readiness-therapist-inperson",
    "name": "Readiness In-Person Clinician",
    "email": "inperson.clinician@example.com",
    "phone": "+26771000010",
    "active": True,
    "supports_in_person": True,
    "supports_virtual": False,
    "specializations": ["Individual Counselling", "Couple Therapy", "Family Systems"],
    "working_days": [0, 1, 2, 3, 4],
    "working_hours_start": "08:00",
    "working_hours_end": "18:00",
    "slot_duration_minutes": 60,
    "default_location": "FCA Clinic Test",
    "virtual_meeting_link_template": None
}

TEST_THERAPIST_VIRTUAL = {
    "id": "readiness-therapist-virtual",
    "name": "Readiness Virtual Specialist",
    "email": "virtual.specialist@example.com",
    "phone": "+26771000020",
    "active": True,
    "supports_in_person": False,
    "supports_virtual": True,
    "specializations": ["Virtual Counselling"],
    "working_days": [0, 1, 2, 3, 4, 5],
    "working_hours_start": "08:00",
    "working_hours_end": "18:00",
    "slot_duration_minutes": 60,
    "default_location": None,
    "virtual_meeting_link_template": "https://meet.example.com/test-room"
}

@pytest_asyncio.fixture
async def readiness_app():
    client = AsyncMongoMockClient()
    mock_db = client["test_foundations_db"]
    # Seed explicit test fixtures
    await mock_db.therapists.insert_one(Therapist(**TEST_THERAPIST_IN_PERSON).model_dump())
    await mock_db.therapists.insert_one(Therapist(**TEST_THERAPIST_VIRTUAL).model_dump())
    app.state.db = mock_db

    # Register test fixture roles in session store
    USERS_DB["staff_user"] = {
        "password_hash": bcrypt.hashpw(b"staffpass123", bcrypt.gensalt()).decode(),
        "role": "staff",
        "name": "Staff Coordinator",
        "therapist_id": None
    }
    USERS_DB["therapist_user"] = {
        "password_hash": bcrypt.hashpw(b"therapistpass123", bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Therapist User",
        "therapist_id": "readiness-therapist-virtual"
    }
    USERS_DB["super_admin"] = {
        "password_hash": bcrypt.hashpw(b"supersecret2026", bcrypt.gensalt()).decode(),
        "role": "super_admin",
        "name": "System Administrator",
        "therapist_id": None
    }
    return app, mock_db

# ==================== 1. Security & RBAC Matrix Audit ====================
@pytest.mark.asyncio
async def test_security_anonymous_rejection(readiness_app):
    test_app, mock_db = readiness_app
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        endpoints = [
            ("GET", "/api/crm/clients"),
            ("POST", "/api/crm/clients"),
            ("GET", "/api/crm/dashboard"),
            ("GET", "/api/bookings"),
            ("POST", "/api/bookings"),
            ("POST", "/api/bookings/multi"),
            ("GET", "/api/therapists"),
            ("POST", "/api/therapists"),
            ("GET", "/api/therapists/blocks"),
            ("GET", "/api/admin-ops/notifications"),
            ("GET", "/api/admin-ops/audit/logs")
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                res = await ac.get(endpoint)
            else:
                res = await ac.post(endpoint, json={})
            assert res.status_code == 401, f"Expected 401 on {endpoint}, got {res.status_code}"

@pytest.mark.asyncio
async def test_rbac_role_isolation(readiness_app):
    test_app, mock_db = readiness_app
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Staff Login
        staff_login = await ac.post("/api/login", json={"username": "staff_user", "password": "staffpass123"})
        assert staff_login.status_code == 200
        
        # Staff cannot access admin audit logs (requires admin/super_admin)
        audit_res = await ac.get("/api/admin-ops/audit/logs")
        assert audit_res.status_code == 403

        # Staff cannot create therapists (requires admin/super_admin)
        t_res = await ac.post("/api/therapists", json={"name": "New T", "email": "t@example.com"})
        assert t_res.status_code == 403

        # Logout
        await ac.post("/api/logout")

        # 2. Therapist Login
        therapist_login = await ac.post("/api/login", json={"username": "therapist_user", "password": "therapistpass123"})
        assert therapist_login.status_code == 200

        # Therapist cannot access admin audit logs
        assert (await ac.get("/api/admin-ops/audit/logs")).status_code == 403

        # 3. Super Admin Login
        await ac.post("/api/logout")
        admin_login = await ac.post("/api/login", json={"username": "super_admin", "password": "supersecret2026"})
        assert admin_login.status_code == 200
        assert (await ac.get("/api/admin-ops/audit/logs")).status_code == 200

# ==================== 2. CRM Client Matching Edge Cases ====================
@pytest.mark.asyncio
async def test_crm_matching_edge_cases(readiness_app):
    _, mock_db = readiness_app

    # Test 1: Email casing and whitespace
    c1, is_new1 = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Tebogo",
        "last_name": "Tau",
        "email": "tebogo.tau@example.com",
        "phone": "+267 71 000 111"
    })
    assert is_new1 is True

    c1_match, is_new1_match = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Tebogo",
        "last_name": "Tau",
        "email": "  TEBOGO.TAU@EXAMPLE.COM  "
    })
    assert is_new1_match is False
    assert c1_match.id == c1.id

    # Test 2: Phone formatting
    c2, is_new2 = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Neo",
        "last_name": "Setso",
        "email": "neo@example.com",
        "phone": "+26772333444"
    })
    assert is_new2 is True

    c2_match, is_new2_match = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Neo S",
        "phone": " +267 (72) 333-444 "
    })
    assert is_new2_match is False
    assert c2_match.id == c2.id

    # Test 3: Same name + same DOB, different email and phone -> Separate clients
    c3, is_new3 = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Tebogo",
        "last_name": "Tau",
        "dob": "1990-01-01",
        "email": "different.tebogo@example.com",
        "phone": "+267 73 999 000"
    })
    assert is_new3 is True
    assert c3.id != c1.id
    assert c3.client_number != c1.client_number

    # Test 4: Multiple intake submissions for same client
    intake1 = await IntakeService.process_intake_submission(mock_db, {
        "full_name": "Test User Sebele",
        "email": "testuser.sebele@example.com",
        "phone": "+267 74 111 222",
        "reason": "Intake 1"
    })
    assert intake1["is_new_client"] is True

    intake2 = await IntakeService.process_intake_submission(mock_db, {
        "full_name": "Test User Sebele",
        "email": "testuser.sebele@example.com",
        "phone": "+267 74 111 222",
        "reason": "Intake 2"
    })
    assert intake2["is_new_client"] is False
    assert intake2["client_id"] == intake1["client_id"]

    intakes = await IntakeService.get_client_intakes(mock_db, intake1["client_id"])
    assert len(intakes) == 2

# ==================== 3. Client Number Concurrency ====================
@pytest.mark.asyncio
async def test_client_number_concurrency(readiness_app):
    _, mock_db = readiness_app

    # Concurrently generate 20 client numbers
    tasks = [CRMService.get_next_client_number(mock_db) for _ in range(20)]
    numbers = await asyncio.gather(*tasks)

    # Confirm all 20 are unique
    assert len(numbers) == 20
    assert len(set(numbers)) == 20
    for num in numbers:
        assert num.startswith("FCA-")

# ==================== 4. Booking Overlap Testing ====================
@pytest.mark.asyncio
async def test_booking_overlap_scenarios(readiness_app):
    _, mock_db = readiness_app

    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Test",
        "last_name": "Client",
        "email": "test.overlap@example.com",
        "phone": "+267 75 000 000"
    })

    # Base Booking: 10:00 - 11:00 UTC
    base_req = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T10:00:00Z",
        ends_at="2026-11-10T11:00:00Z",
        send_notifications=False
    )
    booking, err = await BookingService.create_booking(mock_db, base_req)
    assert err is None
    assert booking is not None

    # Case A: Partial overlap before (09:30 - 10:30) -> REJECT
    req_a = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T09:30:00Z",
        ends_at="2026-11-10T10:30:00Z",
        send_notifications=False
    )
    b_a, err_a = await BookingService.create_booking(mock_db, req_a)
    assert b_a is None
    assert "already has an active appointment" in err_a

    # Case B: Partial overlap after (10:30 - 11:30) -> REJECT
    req_b = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T10:30:00Z",
        ends_at="2026-11-10T11:30:00Z",
        send_notifications=False
    )
    b_b, err_b = await BookingService.create_booking(mock_db, req_b)
    assert b_b is None
    assert "already has an active appointment" in err_b

    # Case C: Complete engulfment (09:00 - 12:00) -> REJECT
    req_c = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T09:00:00Z",
        ends_at="2026-11-10T12:00:00Z",
        send_notifications=False
    )
    b_c, err_c = await BookingService.create_booking(mock_db, req_c)
    assert b_c is None
    assert "already has an active appointment" in err_c

    # Case D: Adjacent back-to-back before (09:00 - 10:00) -> ALLOW
    req_d = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T09:00:00Z",
        ends_at="2026-11-10T10:00:00Z",
        send_notifications=False
    )
    b_d, err_d = await BookingService.create_booking(mock_db, req_d)
    assert err_d is None
    assert b_d is not None

    # Case E: Adjacent back-to-back after (11:00 - 12:00) -> ALLOW
    req_e = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-11-10T11:00:00Z",
        ends_at="2026-11-10T12:00:00Z",
        send_notifications=False
    )
    b_e, err_e = await BookingService.create_booking(mock_db, req_e)
    assert err_e is None
    assert b_e is not None

    # Case F: Cancelled booking should NOT block new booking in that slot
    await BookingService.update_booking_status(
        mock_db, booking.id, BookingStatusUpdateRequest(status="cancelled", cancellation_reason="Client moved")
    )
    req_retry = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="couple",
        session_mode="in_person",
        starts_at="2026-11-10T10:00:00Z",
        ends_at="2026-11-10T11:00:00Z",
        send_notifications=False
    )
    b_retry, err_retry = await BookingService.create_booking(mock_db, req_retry)
    assert err_retry is None
    assert b_retry is not None
    assert b_retry.status == "confirmed"

# ==================== 5. Multi-Booking Batch Atomicity ====================
@pytest.mark.asyncio
async def test_multi_booking_atomicity_and_concurrency(readiness_app):
    _, mock_db = readiness_app

    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Batch",
        "last_name": "Tester",
        "email": "batch.tester@example.com",
        "phone": "+267 76 000 000"
    })

    # Pre-occupy November 18 10:00 UTC
    blocker_req = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-virtual",
        session_type="individual",
        session_mode="virtual",
        starts_at="2026-11-18T10:00:00Z",
        ends_at="2026-11-18T11:00:00Z",
        send_notifications=False
    )
    await BookingService.create_booking(mock_db, blocker_req)

    initial_booking_count = await mock_db.bookings.count_documents({})
    initial_batch_count = await mock_db.booking_batches.count_documents({})

    # Request batch of 4 sessions where slot 3 (Nov 18) conflicts
    batch_req = MultiBookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-virtual",
        session_type="individual",
        session_mode="virtual",
        slots=[
            SingleBookingSlot(starts_at="2026-11-04T10:00:00Z"),
            SingleBookingSlot(starts_at="2026-11-11T10:00:00Z"),
            SingleBookingSlot(starts_at="2026-11-18T10:00:00Z"),  # CONFLICT
            SingleBookingSlot(starts_at="2026-11-25T10:00:00Z")
        ],
        send_notifications=False
    )

    result, err = await BookingService.create_multi_booking(mock_db, batch_req)
    assert result is None
    assert "cannot be booked" in err
    assert "Slot #3" in err

    # Verify ATOMICITY: ZERO new bookings or batches were created
    final_booking_count = await mock_db.bookings.count_documents({})
    final_batch_count = await mock_db.booking_batches.count_documents({})
    assert final_booking_count == initial_booking_count
    assert final_batch_count == initial_batch_count

# ==================== 6. Couple and Family Participants ====================
@pytest.mark.asyncio
async def test_couple_and_family_participants(readiness_app):
    _, mock_db = readiness_app

    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Tshepo",
        "last_name": "Kgosi",
        "email": "tshepo.kgosi@example.com",
        "phone": "+267 77 111 222"
    })

    # Family Booking with 3 participants
    family_req = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="family",
        session_mode="in_person",
        starts_at="2026-12-01T14:00:00Z",
        participants=[
            {"name": "Partner Test", "participant_role": "partner"},
            {"name": "Child Test", "participant_role": "child"}
        ],
        send_notifications=False
    )

    booking, err = await BookingService.create_booking(mock_db, family_req)
    assert err is None
    assert booking.session_type == "family"
    assert len(booking.participants) == 3
    roles = [p.participant_role for p in booking.participants]
    assert "primary_client" in roles
    assert "partner" in roles
    assert "child" in roles

    # Reschedule and confirm participants are preserved
    rescheduled, r_err = await BookingService.reschedule_booking(
        mock_db,
        booking.id,
        BookingRescheduleRequest(new_starts_at="2026-12-01T15:00:00Z", send_notifications=False)
    )
    assert r_err is None
    assert len(rescheduled.participants) == 3

# ==================== 7. Notification Failure Non-Blocking Behavior ====================
@pytest.mark.asyncio
async def test_notification_failure_non_blocking(readiness_app):
    _, mock_db = readiness_app

    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Notification",
        "last_name": "Tester",
        "email": "invalid-email-address",
        "phone": ""
    })

    req = BookingCreateRequest(
        client_id=client.id,
        therapist_id="readiness-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-12-15T10:00:00Z",
        send_notifications=True
    )

    # Booking must still succeed even if notification recipient is invalid
    booking, err = await BookingService.create_booking(mock_db, req)
    assert err is None
    assert booking is not None
    assert booking.status == "confirmed"

    # Notification log should record the failure status
    notif_logs = await NotificationService.list_notifications(mock_db, client_id=client.id)
    assert len(notif_logs) >= 1

# ==================== 8. Authorized FCA Test Clinicians Configuration ====================
@pytest.mark.asyncio
async def test_authorized_fca_test_clinicians_configured():
    # Verify DEFAULT_THERAPISTS contains exactly the two authorized FCA test clinicians
    assert len(DEFAULT_THERAPISTS) == 2
    names = [t["name"] for t in DEFAULT_THERAPISTS]
    assert "Caroline Sithole" in names
    assert "Alpheaus Chiwaze" in names

# ==================== 9. Admin Bootstrap Security Verification ====================
@pytest.mark.asyncio
async def test_admin_bootstrap_security():
    # 1. Without credentials, no admin is created
    os.environ.pop("FCA_BOOTSTRAP_ADMIN_EMAIL", None)
    os.environ.pop("FCA_BOOTSTRAP_ADMIN_PASSWORD", None)
    os.environ.pop("ADMIN_USER", None)
    os.environ.pop("ADMIN_PASSWORD", None)
    USERS_DB.clear()
    bootstrap_super_admin()
    assert len(USERS_DB) == 0

    # 2. With valid credentials, super_admin is created
    os.environ["FCA_BOOTSTRAP_ADMIN_EMAIL"] = "admin@academyfoundations.com"
    os.environ["FCA_BOOTSTRAP_ADMIN_PASSWORD"] = "StrongSecurePassword2026!"
    bootstrap_super_admin()
    assert "admin@academyfoundations.com" in USERS_DB
    admin_entry = USERS_DB["admin@academyfoundations.com"]
    assert admin_entry["role"] == "super_admin"
    assert bcrypt.checkpw(b"StrongSecurePassword2026!", admin_entry["password_hash"].encode())

    # Cleanup
    os.environ.pop("FCA_BOOTSTRAP_ADMIN_EMAIL", None)
    os.environ.pop("FCA_BOOTSTRAP_ADMIN_PASSWORD", None)
    os.environ.pop("ADMIN_USER", None)
    os.environ.pop("ADMIN_PASSWORD", None)
    USERS_DB.clear()
