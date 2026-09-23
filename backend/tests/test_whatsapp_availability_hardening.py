import pytest
from mongomock_motor import AsyncMongoMockClient

from services.whatsapp_booking_bot_fast_slots import (
    AVAILABILITY_DAYS,
    SchedulingAvailabilityError,
    fast_slot_options,
)
from services.scheduling_service import SchedulingService
from services.therapist_service import TherapistService


@pytest.mark.asyncio
async def test_whatsapp_self_service_searches_35_days(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_whatsapp_availability"]

    await db.therapists.insert_one({
        "id": "therapist-caroline-sithole",
        "name": "Caroline Sithole",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": True,
        "specializations": [],
        "working_days": [0, 1, 2, 3, 4],
        "working_hours_start": "08:00",
        "working_hours_end": "17:00",
        "slot_duration_minutes": 60,
    })

    client_doc = {
        "id": "client-1",
        "first_name": "Test",
    }

    observed = {}

    async def fake_slots(db_arg, therapist_id, start_date, days_ahead, session_type="individual", session_mode="virtual", funding_scope="private"):
        observed["days_ahead"] = days_ahead
        return []

    monkeypatch.setattr(SchedulingService, "get_available_slots", staticmethod(fake_slots))

    result = await fast_slot_options(db, client_doc, "virtual", "individual")

    assert result == []
    assert AVAILABILITY_DAYS == 35
    assert observed["days_ahead"] == 35


@pytest.mark.asyncio
async def test_whatsapp_provider_failure_is_not_reported_as_no_slots(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_whatsapp_provider_failure"]

    await db.therapists.insert_one({
        "id": "therapist-caroline-sithole",
        "name": "Caroline Sithole",
        "active": True,
        "supports_in_person": True,
        "supports_virtual": True,
        "specializations": [],
        "working_days": [0, 1, 2, 3, 4],
        "working_hours_start": "08:00",
        "working_hours_end": "17:00",
        "slot_duration_minutes": 60,
    })

    client_doc = {
        "id": "client-2",
        "first_name": "Test",
    }

    async def fail_slots(*args, **kwargs):
        raise RuntimeError("simulated Setmore failure")

    monkeypatch.setattr(SchedulingService, "get_available_slots", staticmethod(fail_slots))

    with pytest.raises(SchedulingAvailabilityError):
        await fast_slot_options(db, client_doc, "virtual", "individual")
