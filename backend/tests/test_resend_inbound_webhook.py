import base64
import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

import server as server_module
from server import app


def _sign(secret_value: str, event_id: str, timestamp: str, raw_body: bytes) -> str:
    secret = secret_value.removeprefix("whsec_")
    key = base64.b64decode(secret)
    signed = f"{event_id}.{timestamp}.".encode("utf-8") + raw_body
    digest = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode("ascii")
    return f"v1,{digest}"


@pytest.fixture
def resend_webhook_app(monkeypatch):
    client = AsyncMongoMockClient()
    mock_db = client["test_resend_webhook"]
    original_db = app.state.db
    app.state.db = mock_db

    webhook_secret = "whsec_" + base64.b64encode(b"foundations-test-webhook-secret").decode("ascii")
    monkeypatch.setattr(server_module, "RESEND_WEBHOOK_SECRET", webhook_secret)
    monkeypatch.setattr(server_module, "RESEND_INBOUND_DOMAIN", "forms.academyfoundations.com")

    yield app, mock_db, webhook_secret
    app.state.db = original_db


@pytest.mark.asyncio
async def test_resend_email_received_webhook_is_verified_and_stored(resend_webhook_app):
    test_app, mock_db, webhook_secret = resend_webhook_app
    event_id = "msg_webhook_001"
    timestamp = str(int(time.time()))
    payload = {
        "type": "email.received",
        "created_at": "2026-09-28T16:55:00.000Z",
        "data": {
            "email_id": "email_received_001",
            "message_id": "<forms-test@example.com>",
            "created_at": "2026-09-28T16:54:59.000Z",
            "from": "Website Form <sender@example.com>",
            "to": ["contact@forms.academyfoundations.com"],
            "subject": "Website contact form",
            "attachments": [],
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "svix-id": event_id,
        "svix-timestamp": timestamp,
        "svix-signature": _sign(webhook_secret, event_id, timestamp, raw),
    }

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/webhooks/resend", content=raw, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    stored_event = await mock_db.resend_webhook_events.find_one({"event_id": event_id}, {"_id": 0})
    assert stored_event["event_type"] == "email.received"

    stored_message = await mock_db.resend_inbound_messages.find_one(
        {"email_id": "email_received_001"},
        {"_id": 0},
    )
    assert stored_message["to"] == ["contact@forms.academyfoundations.com"]
    assert stored_message["source"] == "resend_inbound"
    assert stored_message["status"] == "received"


@pytest.mark.asyncio
async def test_resend_webhook_rejects_invalid_signature(resend_webhook_app):
    test_app, mock_db, _ = resend_webhook_app
    raw = json.dumps({"type": "email.received", "data": {}}).encode("utf-8")

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/webhooks/resend",
            content=raw,
            headers={
                "content-type": "application/json",
                "svix-id": "bad-event",
                "svix-timestamp": str(int(time.time())),
                "svix-signature": "v1,invalid",
            },
        )

    assert response.status_code == 400
    assert await mock_db.resend_webhook_events.count_documents({}) == 0


@pytest.mark.asyncio
async def test_resend_webhook_is_idempotent(resend_webhook_app):
    test_app, mock_db, webhook_secret = resend_webhook_app
    event_id = "msg_webhook_duplicate"
    timestamp = str(int(time.time()))
    payload = {
        "type": "email.received",
        "data": {
            "email_id": "email_duplicate_001",
            "from": "Sender <sender@example.com>",
            "to": ["intake@forms.academyfoundations.com"],
            "subject": "Duplicate test",
            "attachments": [],
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "svix-id": event_id,
        "svix-timestamp": timestamp,
        "svix-signature": _sign(webhook_secret, event_id, timestamp, raw),
    }

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/webhooks/resend", content=raw, headers=headers)
        second = await client.post("/api/webhooks/resend", content=raw, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate_ignored"
    assert await mock_db.resend_webhook_events.count_documents({"event_id": event_id}) == 1
    assert await mock_db.resend_inbound_messages.count_documents({"email_id": "email_duplicate_001"}) == 1


@pytest.mark.asyncio
async def test_resend_webhook_ignores_other_recipient_domains(resend_webhook_app):
    test_app, mock_db, webhook_secret = resend_webhook_app
    event_id = "msg_webhook_other_domain"
    timestamp = str(int(time.time()))
    payload = {
        "type": "email.received",
        "data": {
            "email_id": "email_other_domain",
            "from": "Sender <sender@example.com>",
            "to": ["someone@example.org"],
            "subject": "Not a Foundations form message",
            "attachments": [],
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "svix-id": event_id,
        "svix-timestamp": timestamp,
        "svix-signature": _sign(webhook_secret, event_id, timestamp, raw),
    }

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/webhooks/resend", content=raw, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert await mock_db.resend_inbound_messages.count_documents({}) == 0
