import pytest
from mongomock_motor import AsyncMongoMockClient

from routers.meta_whatsapp_router import (
    _booking_summary,
    _handle_super_admin_assignment_flow,
    _resolve_super_admin_by_whatsapp,
)
from services.booking_service import BookingService
from services.scheduling_service import SchedulingService


@pytest.mark.parametrize('value', ['2026-10-06T12:00:00Z', '2026-10-06T14:00:00+02:00', '2026-10-06T12:00:00'])
def test_admin_booking_summary_uses_cat(value):
    summary = _booking_summary({'starts_at': value, 'session_mode': 'virtual', 'session_type': 'individual'}, 1)
    assert 'Tue 06 Oct 2026, 14:00 CAT' in summary
    assert 'UTC' not in summary


def test_admin_booking_summary_uses_cat_calendar_day():
    summary = _booking_summary({'starts_at': '2026-12-31T22:30:00Z'}, 1)
    assert 'Fri 01 Jan 2027, 00:30 CAT' in summary


@pytest.mark.asyncio
async def test_only_enabled_super_admin_phone_is_authorized():
    client = AsyncMongoMockClient()
    db = client["admin_whatsapp_auth"]

    await db.staff_users.insert_many([
        {
            "user_id": "super@example.com",
            "name": "Super Admin",
            "role": "super_admin",
            "active": True,
            "whatsapp_phone": "+267 71 000 001",
            "whatsapp_admin_enabled": True,
        },
        {
            "user_id": "admin@example.com",
            "name": "Admin",
            "role": "admin",
            "active": True,
            "whatsapp_phone": "+26771000002",
            "whatsapp_admin_enabled": True,
        },
    ])

    authorized = await _resolve_super_admin_by_whatsapp(db, "+26771000001")
    unauthorized = await _resolve_super_admin_by_whatsapp(db, "+26771000002")

    assert authorized["user_id"] == "super@example.com"
    assert unauthorized is None


@pytest.mark.asyncio
async def test_super_admin_can_assign_pending_booking_by_whatsapp(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["admin_whatsapp_assignment"]

    await db.staff_users.insert_one({
        "user_id": "super@example.com",
        "name": "Super Admin",
        "role": "super_admin",
        "active": True,
        "whatsapp_phone": "+26771000001",
        "whatsapp_admin_enabled": True,
    })
    await db.bookings.insert_one({
        "id": "booking-admin-wa-1",
        "client_id": "client-1",
        "status": "pending",
        "assignment_status": "awaiting_assignment",
        "session_type": "individual",
        "session_mode": "virtual",
        "starts_at": "2026-10-12T09:00:00+00:00",
        "ends_at": "2026-10-12T10:00:00+00:00",
    })
    await db.therapists.insert_one({
        "id": "therapist-admin-wa-1",
        "name": "Available Therapist",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": True,
        "specializations": [],
        "working_days": [0, 1, 2, 3, 4, 5, 6],
        "working_hours_start": "08:00",
        "working_hours_end": "18:00",
        "slot_duration_minutes": 60,
    })

    monkeypatch.setattr(SchedulingService, "provider", staticmethod(lambda: "internal"))

    captured = {}

    async def fake_assign(
        db_arg,
        booking_id,
        therapist_id,
        actor_id=None,
        actor_name=None,
    ):
        captured.update({
            "booking_id": booking_id,
            "therapist_id": therapist_id,
            "actor_id": actor_id,
            "actor_name": actor_name,
        })
        return type("Assigned", (), {"id": booking_id})(), None

    monkeypatch.setattr(BookingService, "assign_therapist", staticmethod(fake_assign))

    first = await _handle_super_admin_assignment_flow(db, "+26771000001", "ASSIGN")
    assert "Pending booking requests:" in first
    assert "Individual" in first

    second = await _handle_super_admin_assignment_flow(db, "+26771000001", "1")
    assert "Available therapists:" in second
    assert "Available Therapist" in second

    third = await _handle_super_admin_assignment_flow(db, "+26771000001", "1")
    assert "Therapist assigned successfully" in third

    assert captured["booking_id"] == "booking-admin-wa-1"
    assert captured["therapist_id"] == "therapist-admin-wa-1"
    assert captured["actor_id"] == "super@example.com"


@pytest.mark.asyncio
async def test_non_super_admin_does_not_enter_admin_flow():
    client = AsyncMongoMockClient()
    db = client["admin_whatsapp_reject"]

    await db.staff_users.insert_one({
        "user_id": "ordinary@example.com",
        "name": "Ordinary Admin",
        "role": "admin",
        "active": True,
        "whatsapp_phone": "+26771000003",
        "whatsapp_admin_enabled": True,
    })

    reply = await _handle_super_admin_assignment_flow(db, "+26771000003", "ASSIGN")
    assert reply is None
