import json

import pytest
from mongomock_motor import AsyncMongoMockClient

import services.therapist_notification_service as therapist_notifications
from models import Booking, CRMClient
from services.therapist_notification_service import (
    TherapistNotificationService,
    _meta_error_code,
    _therapist_language_candidates,
)


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.content = json.dumps(body).encode("utf-8")

    def json(self):
        return self._body


def test_meta_error_code_extracts_nested_graph_error():
    response = FakeResponse(
        404,
        {"error": {"message": "(#132001) Template name does not exist in the translation", "code": 132001}},
    )
    assert _meta_error_code(response) == 132001


def test_therapist_language_candidates_are_deduplicated(monkeypatch):
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_THERAPIST_TEMPLATE_LANGUAGE", "en")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_TEMPLATE_LANGUAGE", "en")
    assert _therapist_language_candidates() == ["en", "en_US"]


@pytest.mark.asyncio
async def test_therapist_template_retries_en_us_after_132001(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["therapist_template_locale"]

    therapist = type(
        "Therapist",
        (),
        {
            "id": "therapist-locale-1",
            "name": "Locale Therapist",
            "whatsapp_phone": "+26771000001",
            "whatsapp_notifications_enabled": True,
        },
    )()

    await db.therapists.insert_one({
        "id": "therapist-locale-1",
        "name": "Locale Therapist",
        "active": True,
        "whatsapp_phone": "+26771000001",
        "whatsapp_notifications_enabled": True,
    })

    crm_client = CRMClient(
        id="client-locale-1",
        client_number="FCA-LOCALE-1",
        first_name="Template",
        last_name="Client",
        email="template@example.com",
        phone="+26772000001",
    )
    booking = Booking(
        id="booking-locale-1",
        client_id=crm_client.id,
        therapist_id="therapist-locale-1",
        therapist_name="Locale Therapist",
        assignment_status="awaiting_acceptance",
        session_type="individual",
        session_mode="virtual",
        starts_at="2026-10-15T09:00:00+00:00",
        ends_at="2026-10-15T10:00:00+00:00",
        status="pending",
    )

    monkeypatch.setattr(therapist_notifications, "WHATSAPP_PHONE_NUMBER_ID", "12345")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(
        therapist_notifications,
        "WHATSAPP_THERAPIST_TEMPLATE_NAME",
        "fca_therapist_booking_notification",
    )
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_THERAPIST_TEMPLATE_LANGUAGE", "en")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_TEMPLATE_LANGUAGE", "en")

    attempted = []

    def fake_post(url, json=None, headers=None, timeout=None):
        attempted.append(json["template"]["language"]["code"])
        if json["template"]["language"]["code"] == "en":
            return FakeResponse(
                404,
                {"error": {"message": "(#132001) Template name does not exist in the translation", "code": 132001}},
            )
        return FakeResponse(
            200,
            {"messages": [{"id": "wamid.template-locale-success"}]},
        )

    monkeypatch.setattr(therapist_notifications.requests, "post", fake_post)

    log = await TherapistNotificationService.send_booking_whatsapp(
        db,
        therapist,
        crm_client,
        [booking],
    )

    assert attempted == ["en", "en_US"]
    assert log.status == "sent"
    assert log.provider_reference == "wamid.template-locale-success"


@pytest.mark.asyncio
async def test_non_132001_template_error_does_not_retry(monkeypatch):
    client = AsyncMongoMockClient()
    db = client["therapist_template_no_retry"]

    therapist = type(
        "Therapist",
        (),
        {
            "id": "therapist-no-retry",
            "name": "No Retry Therapist",
            "whatsapp_phone": "+26771000002",
            "whatsapp_notifications_enabled": True,
        },
    )()
    await db.therapists.insert_one({
        "id": "therapist-no-retry",
        "name": "No Retry Therapist",
        "active": True,
        "whatsapp_phone": "+26771000002",
        "whatsapp_notifications_enabled": True,
    })

    crm_client = CRMClient(
        id="client-no-retry",
        client_number="FCA-NORETRY",
        first_name="No",
        last_name="Retry",
        email="noretry@example.com",
        phone="+26772000002",
    )
    booking = Booking(
        id="booking-no-retry",
        client_id=crm_client.id,
        therapist_id="therapist-no-retry",
        therapist_name="No Retry Therapist",
        assignment_status="awaiting_acceptance",
        session_type="individual",
        session_mode="virtual",
        starts_at="2026-10-15T11:00:00+00:00",
        ends_at="2026-10-15T12:00:00+00:00",
        status="pending",
    )

    monkeypatch.setattr(therapist_notifications, "WHATSAPP_PHONE_NUMBER_ID", "12345")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_THERAPIST_TEMPLATE_LANGUAGE", "en")
    monkeypatch.setattr(therapist_notifications, "WHATSAPP_TEMPLATE_LANGUAGE", "en")

    attempted = []

    def fake_post(url, json=None, headers=None, timeout=None):
        attempted.append(json["template"]["language"]["code"])
        return FakeResponse(
            400,
            {"error": {"message": "Parameter mismatch", "code": 132000}},
        )

    monkeypatch.setattr(therapist_notifications.requests, "post", fake_post)

    log = await TherapistNotificationService.send_booking_whatsapp(
        db,
        therapist,
        crm_client,
        [booking],
    )

    assert attempted == ["en"]
    assert log.status == "failed"
