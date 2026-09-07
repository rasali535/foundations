import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient
from models import (
    CRMClientCreate, CRMClientUpdate, CRMNoteCreate,
    TherapistCreate, SingleBookingSlot,
    BookingCreateRequest, MultiBookingCreateRequest,
    BookingRescheduleRequest, BookingStatusUpdateRequest,
    Therapist
)
from services.crm_service import CRMService, normalize_email, normalize_phone
from services.intake_service import IntakeService
from services.therapist_service import TherapistService
from services.booking_service import BookingService
from services.notification_service import NotificationService

TEST_THERAPIST_IN_PERSON = {
    "id": "test-therapist-inperson",
    "name": "Test In-Person Clinician",
    "email": "clinician.inperson@example.com",
    "phone": "+26771000001",
    "active": True,
    "supports_in_person": True,
    "supports_virtual": False,
    "specializations": ["Individual Counselling", "Couple Therapy"],
    "working_days": [0, 1, 2, 3, 4],
    "working_hours_start": "08:00",
    "working_hours_end": "17:00",
    "slot_duration_minutes": 60,
    "default_location": "FCA Test Clinic",
    "virtual_meeting_link_template": None
}

TEST_THERAPIST_VIRTUAL = {
    "id": "test-therapist-virtual",
    "name": "Test Virtual Specialist",
    "email": "specialist.virtual@example.com",
    "phone": "+26771000002",
    "active": True,
    "supports_in_person": False,
    "supports_virtual": True,
    "specializations": ["Virtual Counselling"],
    "working_days": [0, 1, 2, 3, 4, 5],
    "working_hours_start": "08:00",
    "working_hours_end": "18:00",
    "slot_duration_minutes": 60,
    "default_location": None,
    "virtual_meeting_link_template": "https://meet.example.com/test-virtual"
}

TEST_THERAPIST_DUAL = {
    "id": "test-therapist-dual",
    "name": "Test Dual Clinician",
    "email": "clinician.dual@example.com",
    "phone": "+26771000003",
    "active": True,
    "supports_in_person": True,
    "supports_virtual": True,
    "specializations": ["Family Systems"],
    "working_days": [0, 1, 2, 3, 4],
    "working_hours_start": "08:00",
    "working_hours_end": "18:00",
    "slot_duration_minutes": 60,
    "default_location": "FCA Test Clinic",
    "virtual_meeting_link_template": "https://meet.example.com/test-dual"
}

@pytest_asyncio.fixture
async def mock_db():
    client = AsyncMongoMockClient()
    db = client["test_foundations_db"]
    # Seed explicit test fixtures only
    for t in [TEST_THERAPIST_IN_PERSON, TEST_THERAPIST_VIRTUAL, TEST_THERAPIST_DUAL]:
        await db.therapists.insert_one(Therapist(**t).model_dump())
    return db

# ==================== CRM Tests ====================
@pytest.mark.asyncio
async def test_normalization():
    assert normalize_email("  Test.User@EXAMPLE.COM  ") == "test.user@example.com"
    assert normalize_phone("+267 (71) 123-456") == "+26771123456"
    assert normalize_phone(" 082 123 4567 ") == "0821234567"

@pytest.mark.asyncio
async def test_crm_client_creation_and_matching(mock_db):
    # 1. Create initial client
    client_data = {
        "first_name": "TestUser",
        "last_name": "Molefe",
        "email": "testuser.molefe@example.com",
        "phone": "+267 71 111 222",
        "dob": "1990-01-01",
        "gender": "Male"
    }
    client1, is_new = await CRMService.find_or_create_client(mock_db, client_data)
    assert is_new is True
    assert client1.client_number.startswith("FCA-")
    assert client1.email == "testuser.molefe@example.com"

    # 2. Match by exact normalized email
    duplicate_email_data = {
        "first_name": "TestUser M",
        "email": " TESTUSER.MOLEFE@example.com ",
        "phone": "+267 72 999 888"  # different phone
    }
    client2, is_new2 = await CRMService.find_or_create_client(mock_db, duplicate_email_data)
    assert is_new2 is False
    assert client2.id == client1.id
    assert client2.client_number == client1.client_number

    # 3. Match by exact normalized phone
    duplicate_phone_data = {
        "first_name": "T. Molefe",
        "phone": " +267 (71) 111-222 ",
        "email": "different.email@example.com"
    }
    client3, is_new3 = await CRMService.find_or_create_client(mock_db, duplicate_phone_data)
    assert is_new3 is False
    assert client3.id == client1.id

    # 4. Same Name + Same DOB with DIFFERENT Email and DIFFERENT Phone must NOT merge (creates separate client)
    different_person_data = {
        "first_name": "TestUser",
        "last_name": "Molefe",
        "dob": "1990-01-01",
        "email": "entirely.different@example.com",
        "phone": "+267 76 888 777"
    }
    client4, is_new4 = await CRMService.find_or_create_client(mock_db, different_person_data)
    assert is_new4 is True
    assert client4.id != client1.id
    assert client4.client_number != client1.client_number

    # 5. Search client
    results, total = await CRMService.search_clients(mock_db, query="Molefe")
    assert total == 2

@pytest.mark.asyncio
async def test_crm_admin_notes(mock_db):
    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Sarah",
        "last_name": "Dube",
        "email": "sarah.dube@example.com",
        "phone": "+267 72 333 444"
    })

    # Add Note
    note_payload = CRMNoteCreate(content="Client requested Tuesday afternoon sessions.", is_pinned=True)
    note = await CRMService.create_note(mock_db, client.id, note_payload, "admin_user", "Admin")
    assert note.id is not None
    assert note.is_pinned is True

    # List Notes
    notes = await CRMService.list_notes(mock_db, client.id)
    assert len(notes) == 1
    assert notes[0].content == "Client requested Tuesday afternoon sessions."

    # Delete Note
    deleted = await CRMService.delete_note(mock_db, note.id, "admin_user", "Admin")
    assert deleted is True
    notes_after = await CRMService.list_notes(mock_db, client.id)
    assert len(notes_after) == 0

    # Verify Note Deletion is audited in activity log without leaking content
    audit_logs = await mock_db.crm_activity_log.find({"client_id": client.id, "action": "note_deleted"}).to_list(10)
    assert len(audit_logs) == 1
    assert audit_logs[0]["metadata"]["note_id"] == note.id
    assert "content" not in audit_logs[0]["metadata"]

# ==================== Intake Submission Tests ====================
@pytest.mark.asyncio
async def test_intake_submission_and_linking(mock_db):
    payload = {
        "full_name": "Tebogo Phiri",
        "email": "tebogo.phiri@example.com",
        "phone": "+267 74 555 666",
        "dob": "1992-05-15",
        "reason_for_seeking_therapy": "Workplace stress and burnout",
        "safety_screen": {
            "self_harm": "No",
            "harm_others": "No",
            "unsafe_environment": "No",
            "abuse_experienced": "No"
        }
    }
    result = await IntakeService.process_intake_submission(mock_db, payload)
    assert result["status"] == "intake_received"
    assert result["is_new_client"] is True
    assert result["triage_level"] == "ROUTINE_COUNSELLING"

    # Second intake from same client
    payload2 = {
        "full_name": "Tebogo Phiri",
        "email": "tebogo.phiri@example.com",
        "phone": "+267 74 555 666",
        "reason_for_seeking_therapy": "Follow-up session request",
        "safety_screen": {"self_harm": "No"}
    }
    result2 = await IntakeService.process_intake_submission(mock_db, payload2)
    assert result2["is_new_client"] is False
    assert result2["client_id"] == result["client_id"]

    intakes = await IntakeService.get_client_intakes(mock_db, result["client_id"])
    assert len(intakes) == 2

# ==================== Therapist Routing Tests ====================
@pytest.mark.asyncio
async def test_therapist_routing(mock_db):
    virtual_t = await TherapistService.get_therapist_by_id(mock_db, "test-therapist-virtual")
    assert virtual_t is not None
    assert virtual_t.supports_in_person is False
    assert virtual_t.supports_virtual is True

    # 1. Routing in_person to Virtual-only therapist must FAIL
    t, err = await TherapistService.validate_and_route_therapist(
        mock_db, session_mode="in_person", therapist_id="test-therapist-virtual"
    )
    assert t is None
    assert "does not support In-person" in err

    # 2. Routing virtual to Virtual-only therapist must SUCCEED
    t_v, err_v = await TherapistService.validate_and_route_therapist(
        mock_db, session_mode="virtual", therapist_id="test-therapist-virtual"
    )
    assert err_v is None
    assert t_v.id == "test-therapist-virtual"

# ==================== Booking & Double-Booking Tests ====================
@pytest.mark.asyncio
async def test_booking_creation_and_conflict_rejection(mock_db):
    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Lorato",
        "last_name": "Sechele",
        "email": "lorato@example.com",
        "phone": "+267 75 000 111"
    })

    req1 = BookingCreateRequest(
        client_id=client.id,
        therapist_id="test-therapist-inperson",
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-10-12T09:00:00Z",
        ends_at="2026-10-12T10:00:00Z",
        send_notifications=False
    )
    booking1, err1 = await BookingService.create_booking(mock_db, req1)
    assert err1 is None
    assert booking1 is not None
    assert booking1.status == "confirmed"

    # Conflict 1: Exact duplicate time
    booking_conflict, err_conflict = await BookingService.create_booking(mock_db, req1)
    assert booking_conflict is None
    assert "already has an active appointment" in err_conflict

    # Conflict 2: Overlapping time (09:30 to 10:30)
    req_overlap = BookingCreateRequest(
        client_id=client.id,
        therapist_id="test-therapist-inperson",
        session_type="couple",
        session_mode="in_person",
        starts_at="2026-10-12T09:30:00Z",
        ends_at="2026-10-12T10:30:00Z",
        send_notifications=False
    )
    booking_overlap, err_overlap = await BookingService.create_booking(mock_db, req_overlap)
    assert booking_overlap is None
    assert "already has an active appointment" in err_overlap

# ==================== Monthly Multi-Booking Tests ====================
@pytest.mark.asyncio
async def test_multi_booking_and_independent_lifecycle(mock_db):
    client, _ = await CRMService.find_or_create_client(mock_db, {
        "first_name": "Mpho",
        "last_name": "TestClient",
        "email": "mpho.test@example.com",
        "phone": "+267 76 222 333"
    })

    # 4 Monthly Sessions across October
    multi_req = MultiBookingCreateRequest(
        client_id=client.id,
        therapist_id="test-therapist-dual",
        session_type="family",
        session_mode="virtual",
        slots=[
            SingleBookingSlot(starts_at="2026-10-05T14:00:00Z"),
            SingleBookingSlot(starts_at="2026-10-12T14:00:00Z"),
            SingleBookingSlot(starts_at="2026-10-19T14:00:00Z"),
            SingleBookingSlot(starts_at="2026-10-26T14:00:00Z"),
        ],
        participants=[
            {"name": "Spouse Test", "participant_role": "partner"},
            {"name": "Junior Test", "participant_role": "child"}
        ],
        send_notifications=False
    )

    batch_res, err = await BookingService.create_multi_booking(mock_db, multi_req)
    assert err is None
    assert batch_res["total_created"] == 4
    created_bookings = batch_res["bookings"]

    # Verify each booking is independent
    b1 = created_bookings[0]
    b2 = created_bookings[1]
    b3 = created_bookings[2]
    b4 = created_bookings[3]

    # Reschedule b1 to 15:00 on the same day
    rescheduled_b1, res_err = await BookingService.reschedule_booking(
        mock_db,
        b1.id,
        BookingRescheduleRequest(new_starts_at="2026-10-05T15:00:00Z", reason="Client work conflict", send_notifications=False)
    )
    assert res_err is None
    assert rescheduled_b1.starts_at == "2026-10-05T15:00:00+00:00"

    # Cancel b2
    cancelled_b2, can_err = await BookingService.update_booking_status(
        mock_db,
        b2.id,
        BookingStatusUpdateRequest(status="cancelled", cancellation_reason="Client travel", send_notifications=False)
    )
    assert can_err is None
    assert cancelled_b2.status == "cancelled"

    # Confirm other appointments (b3 and b4) remain intact
    b3_check = await mock_db.bookings.find_one({"id": b3.id})
    b4_check = await mock_db.bookings.find_one({"id": b4.id})
    assert b3_check["status"] == "confirmed"
    assert b4_check["status"] == "confirmed"
