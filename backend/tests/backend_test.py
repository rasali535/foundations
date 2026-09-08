"""
Backend API contract tests for Foundations Counselling Academy.

Aligned with the secured production API (v2.1.0).

Changes from legacy version:
  - TestHealth: expects status == "operational" (not "ok")
  - TestContact: GET /contact is now auth-protected (staff/admin/super_admin required).
    The test verifies the POST still works and that the list endpoint correctly
    returns 401 for unauthenticated callers.
  - TestChat: GET /chat/leads is now auth-protected.
    The /chat/history/<session_id> endpoint has been removed in v2.1.0;
    test updated to verify POST /chat/message round-trip only.
    Chat history retrieval is now handled by the admin session interface.
"""
import os
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load frontend .env to get the configured backend URL
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health ----------
class TestHealth:
    def test_root(self, session):
        """Root health endpoint returns operational status."""
        r = session.get(f"{API}/", timeout=20)
        assert r.status_code == 200
        data = r.json()
        # Production API returns "operational" (not legacy "ok")
        assert data.get("status") == "operational"
        assert "service" in data
        assert "version" in data


# ---------- Contact ----------
class TestContact:
    def test_create_contact(self, session):
        """Unauthenticated contact form submission is accepted (public route)."""
        payload = {
            "name": "TEST_User",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "company": "TEST_Co",
            "phone": "+267 71 000 000",
            "inquiry_type": "EAP & Counselling",
            "message": "TEST_message hello",
        }
        r = session.post(f"{API}/contact", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == payload["name"]
        assert body["email"] == payload["email"]
        assert body["message"] == payload["message"]
        assert "id" in body and isinstance(body["id"], str)
        assert "created_at" in body

    def test_list_contacts_requires_auth(self, session):
        """GET /contact is protected — unauthenticated callers receive 401."""
        r = session.get(f"{API}/contact", timeout=20)
        assert r.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated GET /contact, got {r.status_code}"
        )

    def test_contact_invalid_email(self, session):
        """Invalid email is rejected with 400 or 422."""
        r = session.post(
            f"{API}/contact",
            json={"name": "x", "email": "not-an-email", "message": "hi"},
            timeout=20,
        )
        assert r.status_code in (400, 422)


# ---------- Chat ----------
class TestChat:
    def test_chat_message(self, session):
        """Public chat message endpoint is accessible and returns a reply."""
        session_id = f"test_session_{uuid.uuid4().hex[:10]}"
        r = session.post(
            f"{API}/chat/message",
            json={"session_id": session_id, "message": "Hi, what services do you offer?"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["session_id"] == session_id
        assert isinstance(data["reply"], str)
        assert len(data["reply"].strip()) > 0

    def test_chat_history_endpoint_removed(self, session):
        """
        The /chat/history/<session_id> endpoint was removed in v2.1.0.
        Chat message persistence is accessible only via the authenticated admin interface.
        This test confirms a 404 is returned (endpoint no longer exists).
        """
        r = session.get(f"{API}/chat/history/nonexistent_session", timeout=20)
        assert r.status_code == 404, (
            f"Expected 404 for removed /chat/history endpoint, got {r.status_code}"
        )

    def test_capture_chat_lead(self, session):
        """Unauthenticated chat lead capture (public route) is accepted."""
        payload = {
            "name": "TEST_Lead",
            "email": f"lead_{uuid.uuid4().hex[:6]}@example.com",
            "company": "TEST_Co",
            "phone": "+26771",
            "inquiry_type": "Corporate Training",
            "session_id": f"test_session_{uuid.uuid4().hex[:10]}",
            "notes": "TEST_notes",
        }
        r = session.post(f"{API}/chat/lead", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        lead = r.json()
        assert lead["name"] == payload["name"]
        assert lead["email"] == payload["email"]
        assert "id" in lead and "created_at" in lead

    def test_list_chat_leads_requires_auth(self, session):
        """GET /chat/leads is protected — unauthenticated callers receive 401."""
        r = session.get(f"{API}/chat/leads", timeout=20)
        assert r.status_code == 401, (
            f"Expected 401 Unauthorized for unauthenticated GET /chat/leads, got {r.status_code}"
        )
