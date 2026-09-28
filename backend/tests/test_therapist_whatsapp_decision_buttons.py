import json

import pytest
from mongomock_motor import AsyncMongoMockClient

from models import Booking
from routers.meta_whatsapp_router import (
    _extract_booking_decision_payload,
    _handle_therapist_booking_decision,
)


def test_extracts_template_quick_reply_payload():
    message = {
        "type": "button",
        "button": {
            "text": "Accept",
            "payload": "FCA_BOOKING_ACCEPT:booking-12345678",
        },
    }
    assert _extract_booking_decision_payload(message) == "FCA_BOOKING_ACCEPT:booking-12345678"


@pytest.mark.asyncio
async def test_accept_button_routes_to_booking_decision(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["therapist_button_flow"]

    await db.therapists.insert_one({
        "id": "therapist-button-1",
        "name": "Button Therapist",
        "active": True,
        "whatsapp_phone": "+267 71 234 567",
    })

    captured = {}

    async def fake_decision(
        db_arg,
        booking_id,
        therapist_id,
        decision,
        reason=None,
        actor_id=None,
        actor_name=None,
    ):
        captured.update({
            "booking_id": booking_id,
            "therapist_id": therapist_id,
            "decision": decision,
            "actor_id": actor_id,
            "actor_name": actor_name,
        })
        return Booking(
            id=booking_id,
            client_id="client-1",
            therapist_id=therapist_id,
            therapist_name="Button Therapist",
            assignment_status="accepted",
            session_type="individual",
            session_mode="virtual",
            starts_at="2026-10-10T09:00:00+00:00",
            ends_at="2026-10-10T10:00:00+00:00",
            status="confirmed",
        ), None

    from services.booking_service import BookingService
    monkeypatch.setattr(BookingService, "therapist_decision", staticmethod(fake_decision))

    reply = await _handle_therapist_booking_decision(
        db,
        "+26771234567",
        "FCA_BOOKING_ACCEPT:booking-12345678",
    )

    assert captured["booking_id"] == "booking-12345678"
    assert captured["therapist_id"] == "therapist-button-1"
    assert captured["decision"] == "accept"
    assert "Appointment accepted" in reply


@pytest.mark.asyncio
async def test_decline_button_returns_for_reassignment(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["therapist_button_decline"]

    await db.therapists.insert_one({
        "id": "therapist-button-2",
        "name": "Decline Therapist",
        "active": True,
        "whatsapp_phone": "+26771234568",
    })

    async def fake_decision(*args, **kwargs):
        return Booking(
            id="booking-87654321",
            client_id="client-2",
            therapist_id=None,
            therapist_name=None,
            assignment_status="declined",
            session_type="individual",
            session_mode="in_person",
            starts_at="2026-10-10T11:00:00+00:00",
            ends_at="2026-10-10T12:00:00+00:00",
            status="pending",
        ), None

    from services.booking_service import BookingService
    monkeypatch.setattr(BookingService, "therapist_decision", staticmethod(fake_decision))

    reply = await _handle_therapist_booking_decision(
        db,
        "+26771234568",
        "FCA_BOOKING_DECLINE:booking-87654321",
    )

    assert "Appointment declined" in reply
    assert "reassignment" in reply.lower()


def test_therapist_template_payload_includes_two_quick_reply_components():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "services"
        / "therapist_notification_service.py"
    ).read_text(encoding="utf-8")

    assert '"sub_type": "quick_reply"' in source
    assert 'FCA_BOOKING_ACCEPT:' in source
    assert 'FCA_BOOKING_DECLINE:' in source
