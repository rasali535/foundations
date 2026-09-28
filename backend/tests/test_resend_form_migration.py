import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

import services.notification_service as notification_module
from server import app, RATE_LIMIT_STORE
from services.notification_service import NotificationService


@pytest.fixture
def form_test_app():
    RATE_LIMIT_STORE.clear()
    client = AsyncMongoMockClient()
    mock_db = client["test_form_migration"]
    original_db = app.state.db
    app.state.db = mock_db
    yield app, mock_db
    app.state.db = original_db


@pytest.mark.asyncio
async def test_contact_is_saved_before_resend_delivery_state(form_test_app, monkeypatch):
    test_app, mock_db = form_test_app

    async def fake_contact_delivery(submission):
        stored = await mock_db.contact_submissions.find_one({"id": submission["id"]})
        assert stored is not None
        return {
            "admin_notification_status": "sent",
            "admin_notification_reference": "resend-admin-123",
            "admin_notification_error": None,
            "acknowledgement_status": "sent",
            "acknowledgement_reference": "resend-ack-456",
            "acknowledgement_error": None,
        }

    monkeypatch.setattr(NotificationService, "send_contact_notifications", fake_contact_delivery)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/contact", json={
            "name": "Jane Example",
            "email": "jane@example.com",
            "company": "Example Holdings",
            "phone": "+26770000000",
            "inquiry_type": "Corporate Training",
            "message": "Please contact us about a team programme.",
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["admin_notification_status"] == "sent"
    assert payload["acknowledgement_status"] == "sent"

    stored = await mock_db.contact_submissions.find_one({"id": payload["id"]}, {"_id": 0})
    assert stored["admin_notification_status"] == "sent"
    assert stored["admin_notification_reference"] == "resend-admin-123"
    assert stored["acknowledgement_status"] == "sent"
    assert stored["acknowledgement_reference"] == "resend-ack-456"


@pytest.mark.asyncio
async def test_contact_record_survives_resend_failure(form_test_app, monkeypatch):
    test_app, mock_db = form_test_app

    async def fake_contact_failure(submission):
        return {
            "admin_notification_status": "failed",
            "admin_notification_reference": None,
            "admin_notification_error": "Resend delivery rejected: HTTP 503",
            "acknowledgement_status": "failed",
            "acknowledgement_reference": None,
            "acknowledgement_error": "Resend delivery rejected: HTTP 503",
        }

    monkeypatch.setattr(NotificationService, "send_contact_notifications", fake_contact_failure)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/contact", json={
            "name": "Stored First",
            "email": "stored@example.com",
            "message": "This enquiry must not be lost.",
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["admin_notification_status"] == "failed"

    stored = await mock_db.contact_submissions.find_one({"id": payload["id"]}, {"_id": 0})
    assert stored is not None
    assert stored["message"] == "This enquiry must not be lost."
    assert stored["admin_notification_status"] == "failed"


@pytest.mark.asyncio
async def test_chat_lead_is_saved_then_notified(form_test_app, monkeypatch):
    test_app, mock_db = form_test_app

    async def fake_lead_delivery(lead):
        stored = await mock_db.chatbot_leads.find_one({"id": lead["id"]})
        assert stored is not None
        return {
            "notification_status": "sent",
            "notification_reference": "resend-lead-789",
            "notification_error": None,
        }

    monkeypatch.setattr(NotificationService, "send_chat_lead_notification", fake_lead_delivery)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chat/lead", json={
            "name": "Chat Lead",
            "email": "lead@example.com",
            "company": "Lead Corp",
            "session_id": "chat-session-1",
            "notes": "Asked for EAP pricing.",
        })

    assert response.status_code == 200
    assert response.json()["notification_status"] == "sent"

    stored = await mock_db.chatbot_leads.find_one({"session_id": "chat-session-1"}, {"_id": 0})
    assert stored["notification_status"] == "sent"
    assert stored["notification_reference"] == "resend-lead-789"


@pytest.mark.asyncio
async def test_resend_transport_uses_verified_sender_and_reply_to(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b'{"id":"email_resend_123"}'

        def json(self):
            return {"id": "email_resend_123"}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(notification_module, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(notification_module, "EMAIL_FROM", "Foundations Counselling Academy <notifications@academyfoundations.com>")
    monkeypatch.setattr(notification_module, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(notification_module.requests, "post", fake_post)

    ok, reference, error = await NotificationService.send_email_message(
        "info@academyfoundations.com",
        "Test notification",
        "<p>Hello</p>",
        reply_to="visitor@example.com",
    )

    assert ok is True
    assert reference == "email_resend_123"
    assert error is None
    assert captured["json"]["from"] == "Foundations Counselling Academy <notifications@academyfoundations.com>"
    assert captured["json"]["to"] == ["info@academyfoundations.com"]
    assert captured["json"]["reply_to"] == "visitor@example.com"


@pytest.mark.asyncio
async def test_intake_resend_alert_excludes_clinical_content(form_test_app, monkeypatch):
    test_app, mock_db = form_test_app
    captured = {}

    async def fake_secure_intake_alert(payload):
        captured.update(payload)
        return {
            "notification_status": "sent",
            "notification_reference": "resend-intake-safe-123",
            "notification_error": None,
        }

    monkeypatch.setattr(NotificationService, "send_secure_intake_alert", fake_secure_intake_alert)

    distinctive_reason = "DISTINCTIVE_PRIVATE_THERAPY_REASON"
    distinctive_risk = "DISTINCTIVE_PRIVATE_SAFETY_DETAIL"
    distinctive_contact = "DISTINCTIVE_EMERGENCY_CONTACT"

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/clinical/intake", json={
            "full_name": "Privacy Test Client",
            "dob": "1990-01-01",
            "phone": "+26770000111",
            "email": "privacy-test@example.com",
            "preferred_contact_method": "Email",
            "emergency_contact_name": distinctive_contact,
            "emergency_contact_relationship": "Relative",
            "emergency_contact_phone": "+26770000222",
            "reason_for_seeking_therapy": distinctive_reason,
            "support_needed": ["Stress"],
            "wellbeing_symptoms": ["Anxiety"],
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "Yes",
                "risk_explanation": distinctive_risk,
            },
            "previous_mental_health_support": "No",
            "current_medication": "No",
            "consent_acknowledged": True,
            "typed_signature": "Privacy Test Client",
            "consent_date": "2026-09-28",
        })

    assert response.status_code == 200
    result = response.json()
    assert set(captured.keys()) == {"intake_id", "created_at", "source_type"}
    assert captured["intake_id"] == result["intake_id"]

    serialized_alert = str(captured)
    assert distinctive_reason not in serialized_alert
    assert distinctive_risk not in serialized_alert
    assert distinctive_contact not in serialized_alert
    assert "privacy-test@example.com" not in serialized_alert
    assert "Privacy Test Client" not in serialized_alert

    stored = await mock_db.crm_intake_submissions.find_one(
        {"id": result["intake_id"]},
        {"_id": 0}
    )
    assert stored["notification_status"] == "sent"
    assert stored["notification_reference"] == "resend-intake-safe-123"
