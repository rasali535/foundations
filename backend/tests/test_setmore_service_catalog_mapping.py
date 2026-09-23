import pytest
from mongomock_motor import AsyncMongoMockClient

from services.setmore_service import SetmoreService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "session_type,session_mode,expected_name,expected_key",
    [
        ("individual", "virtual", "Virtual Counseling sessions", "svc-virtual"),
        ("individual", "in_person", "one-on-one Counseling Session", "svc-one-on-one"),
        ("couple", "in_person", "Couple's Counselling", "svc-couple"),
    ],
)
async def test_actual_fca_setmore_service_names_are_selected(
    monkeypatch, session_type, session_mode, expected_name, expected_key
):
    client = AsyncMongoMockClient()
    db = client["test_setmore_service_mapping"]

    rows = [
        {"key": "svc-premarital", "service_name": "Pre-Marital Counselling", "duration": 50},
        {"key": "svc-couple", "service_name": "Couple's Counselling", "duration": 50},
        {"key": "svc-grief", "service_name": "Grief Counselling", "duration": 50},
        {"key": "svc-virtual", "service_name": "Virtual Counseling sessions", "duration": 50},
        {"key": "svc-one-on-one", "service_name": "one-on-one Counseling Session", "duration": 50},
    ]

    async def fake_services(cls):
        return rows

    async def fake_categories(cls):
        return []

    monkeypatch.setattr(SetmoreService, "services", classmethod(fake_services))
    monkeypatch.setattr(SetmoreService, "service_categories", classmethod(fake_categories))

    key = await SetmoreService.resolve_service_key(db, session_type, session_mode)

    assert key == expected_key
    mapping = await db.scheduling_service_mappings.find_one({
        "provider": "setmore",
        "session_type": session_type,
        "session_mode": session_mode,
    })
    assert mapping["service_key"] == expected_key
    assert mapping["service_name"] == expected_name
    assert mapping["service_duration"] == 50


@pytest.mark.asyncio
async def test_available_slots_use_setmore_50_minute_duration(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_setmore_slot_duration"]

    async def fake_staff_key(cls, db_arg, therapist_id):
        return "staff-caroline"

    async def fake_service_key(cls, db_arg, session_type, session_mode):
        await db_arg.scheduling_service_mappings.update_one(
            {
                "provider": "setmore",
                "session_type": session_type,
                "session_mode": session_mode,
            },
            {
                "$set": {
                    "service_key": "svc-virtual",
                    "service_name": "Virtual Counseling sessions",
                    "service_duration": 50,
                }
            },
            upsert=True,
        )
        return "svc-virtual"

    async def fake_api(cls, method, path, **kwargs):
        return {
            "response": True,
            "data": {
                "slots": {
                    "2026-09-24": ["10:00 AM"]
                }
            },
        }

    monkeypatch.setattr(SetmoreService, "resolve_staff_key", classmethod(fake_staff_key))
    monkeypatch.setattr(SetmoreService, "resolve_service_key", classmethod(fake_service_key))
    monkeypatch.setattr(SetmoreService, "_api", classmethod(fake_api))

    slots = await SetmoreService.available_slots(
        db,
        therapist_id="therapist-caroline-sithole",
        start_date="2026-09-24",
        days_ahead=1,
        session_type="individual",
        session_mode="virtual",
    )

    assert len(slots) == 1
    assert slots[0]["starts_at"].endswith("10:00:00+02:00")
    assert slots[0]["ends_at"].endswith("10:50:00+02:00")
