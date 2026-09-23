import pytest
from mongomock_motor import AsyncMongoMockClient

from services.setmore_service import SetmoreError, SetmoreService


@pytest.mark.asyncio
async def test_caroline_resolves_by_exact_setmore_name(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_setmore_staff_mapping"]

    await db.therapists.insert_one({
        "id": "therapist-caroline-sithole",
        "name": "Caroline Sithole",
        "active": True,
    })

    async def fake_staffs(cls):
        return [{
            "key": "setmore-caroline-key",
            "first_name": "Caroline",
            "last_name": "Sithole",
        }]

    monkeypatch.setattr(SetmoreService, "staffs", classmethod(fake_staffs))

    key = await SetmoreService.resolve_staff_key(db, "therapist-caroline-sithole")

    assert key == "setmore-caroline-key"
    stored = await db.therapists.find_one({"id": "therapist-caroline-sithole"})
    assert stored["setmore_staff_key"] == "setmore-caroline-key"


@pytest.mark.asyncio
async def test_single_caroline_staff_does_not_fallback_to_alpheaus(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_setmore_staff_mapping"]

    await db.therapists.insert_one({
        "id": "therapist-alpheaus-chiwaze",
        "name": "Alpheaus Chiwaze",
        "active": True,
    })

    async def fake_staffs(cls):
        return [{
            "key": "setmore-caroline-key",
            "first_name": "Caroline",
            "last_name": "Sithole",
        }]

    monkeypatch.setattr(SetmoreService, "staffs", classmethod(fake_staffs))

    with pytest.raises(SetmoreError, match="staff mapping is missing or ambiguous"):
        await SetmoreService.resolve_staff_key(db, "therapist-alpheaus-chiwaze")

    stored = await db.therapists.find_one({"id": "therapist-alpheaus-chiwaze"})
    assert "setmore_staff_key" not in stored


@pytest.mark.asyncio
async def test_stale_alpheaus_mapping_is_not_replaced_with_caroline(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["test_setmore_staff_mapping"]

    await db.therapists.insert_one({
        "id": "therapist-alpheaus-chiwaze",
        "name": "Alpheaus Chiwaze",
        "setmore_staff_key": "old-alpheaus-key",
        "active": True,
    })

    async def fake_staffs(cls):
        return [{
            "key": "setmore-caroline-key",
            "first_name": "Caroline",
            "last_name": "Sithole",
        }]

    monkeypatch.setattr(SetmoreService, "staffs", classmethod(fake_staffs))

    with pytest.raises(SetmoreError, match="staff mapping is missing or ambiguous"):
        await SetmoreService.resolve_staff_key(db, "therapist-alpheaus-chiwaze")

    stored = await db.therapists.find_one({"id": "therapist-alpheaus-chiwaze"})
    assert stored["setmore_staff_key"] == "old-alpheaus-key"
