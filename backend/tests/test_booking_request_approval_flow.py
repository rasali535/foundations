import pytest
from mongomock_motor import AsyncMongoMockClient

from models import BookingCreateRequest
from services.booking_service import BookingService
from services.notification_service import NotificationService
from services.therapist_notification_service import TherapistNotificationService
from services.scheduling_service import SchedulingService


async def _seed(db):
    await db.crm_clients.insert_one({
        "id": "client-pending-1",
        "client_number": "FCA-PENDING-1",
        "first_name": "Pending",
        "last_name": "Client",
        "email": "pending@example.com",
        "phone": "+26770000001",
        "status": "active",
        "tags": [],
    })
    await db.therapists.insert_one({
        "id": "therapist-pending-1",
        "name": "Assigned Clinician",
        "email": "clinician@example.com",
        "phone": "+26770000002",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": True,
        "specializations": ["Individual Counselling"],
        "working_days": [0, 1, 2, 3, 4, 5, 6],
        "working_hours_start": "08:00",
        "working_hours_end": "18:00",
        "slot_duration_minutes": 60,
        "default_location": "FCA Clinic",
        "whatsapp_notifications_enabled": False,
    })


@pytest.mark.asyncio
async def test_request_assign_accept_lifecycle(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["booking_request_flow"]
    await _seed(db)

    monkeypatch.setattr(SchedulingService, "provider", staticmethod(lambda: "internal"))

    async def no_therapist_message(*args, **kwargs):
        return None

    email_calls = []
    whatsapp_calls = []

    async def fake_email(db_arg, crm_client, bookings, booking_batch_id=None):
        email_calls.append(bookings[0].id)
        return None

    async def fake_whatsapp(db_arg, crm_client, bookings, booking_batch_id=None):
        whatsapp_calls.append(bookings[0].id)
        return None

    monkeypatch.setattr(TherapistNotificationService, "send_booking_whatsapp", staticmethod(no_therapist_message))
    monkeypatch.setattr(NotificationService, "send_booking_email", staticmethod(fake_email))
    monkeypatch.setattr(NotificationService, "send_booking_whatsapp", staticmethod(fake_whatsapp))

    request = BookingCreateRequest(
        client_id="client-pending-1",
        therapist_id=None,
        session_type="individual",
        session_mode="in_person",
        starts_at="2026-10-06T09:00:00+00:00",
        ends_at="2026-10-06T10:00:00+00:00",
        send_notifications=False,
        source="website_intake",
    )

    pending, error = await BookingService.create_booking_request(
        db, request, actor_id="public_intake", actor_name="Website Intake"
    )
    assert error is None
    assert pending.status == "pending"
    assert pending.assignment_status == "awaiting_assignment"
    assert pending.therapist_id is None
    assert pending.setmore_appointment_id is None
    assert email_calls == []
    assert whatsapp_calls == []

    assigned, error = await BookingService.assign_therapist(
        db,
        pending.id,
        "therapist-pending-1",
        actor_id="super-admin-1",
        actor_name="Super Admin",
    )
    assert error is None
    assert assigned.status == "pending"
    assert assigned.assignment_status == "awaiting_acceptance"
    assert assigned.therapist_id == "therapist-pending-1"
    assert email_calls == []
    assert whatsapp_calls == []

    confirmed, error = await BookingService.therapist_decision(
        db,
        pending.id,
        "therapist-pending-1",
        "accept",
        actor_id="therapist-user-1",
        actor_name="Assigned Clinician",
    )
    assert error is None
    assert confirmed.status == "confirmed"
    assert confirmed.assignment_status == "accepted"
    assert confirmed.therapist_id == "therapist-pending-1"
    assert email_calls == [pending.id]
    assert whatsapp_calls == [pending.id]


@pytest.mark.asyncio
async def test_decline_returns_request_for_reassignment(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["booking_decline_flow"]
    await _seed(db)
    monkeypatch.setattr(SchedulingService, "provider", staticmethod(lambda: "internal"))

    async def no_therapist_message(*args, **kwargs):
        return None

    monkeypatch.setattr(TherapistNotificationService, "send_booking_whatsapp", staticmethod(no_therapist_message))

    pending, error = await BookingService.create_booking_request(
        db,
        BookingCreateRequest(
            client_id="client-pending-1",
            session_type="individual",
            session_mode="virtual",
            starts_at="2026-10-07T10:00:00+00:00",
            ends_at="2026-10-07T11:00:00+00:00",
            send_notifications=False,
            source="whatsapp",
        ),
    )
    assert error is None

    assigned, error = await BookingService.assign_therapist(
        db, pending.id, "therapist-pending-1", actor_id="super-admin-1"
    )
    assert error is None

    declined, error = await BookingService.therapist_decision(
        db,
        pending.id,
        "therapist-pending-1",
        "decline",
        reason="Unavailable for this case",
        actor_id="therapist-user-1",
    )
    assert error is None
    assert declined.status == "pending"
    assert declined.assignment_status == "declined"
    assert declined.therapist_id is None
    assert declined.therapist_name is None
    assert declined.therapist_decline_reason == "Unavailable for this case"


def test_public_and_whatsapp_copy_describe_request_not_confirmation():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    intake_source = (root / "frontend" / "src" / "pages" / "IntakeForm.js").read_text(encoding="utf-8")
    wa_source = (root / "backend" / "services" / "whatsapp_booking_bot_service.py").read_text(encoding="utf-8")
    router_source = (root / "backend" / "routers" / "booking_router.py").read_text(encoding="utf-8")

    assert "Booking request received" in intake_source
    assert "Awaiting confirmation" in intake_source
    assert "Your booking request has been received" in wa_source
    assert "Awaiting therapist confirmation" in wa_source
    assert "BookingService.create_booking_request" in router_source
    assert "require_super_admin" in router_source
