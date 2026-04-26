"""Backend API tests for Foundations Counselling Academy."""
import os
import time
import uuid
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load frontend .env to get the public REACT_APP_BACKEND_URL
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
        r = session.get(f"{API}/", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        assert "service" in data


# ---------- Contact ----------
class TestContact:
    def test_create_and_list_contact(self, session):
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

        # Persistence check
        r2 = session.get(f"{API}/contact", timeout=20)
        assert r2.status_code == 200
        items = r2.json()
        assert isinstance(items, list)
        # _id must be excluded
        for it in items[:5]:
            assert "_id" not in it
        ids = [i["id"] for i in items]
        assert body["id"] in ids

    def test_contact_invalid_email(self, session):
        r = session.post(
            f"{API}/contact",
            json={"name": "x", "email": "not-an-email", "message": "hi"},
            timeout=20,
        )
        assert r.status_code in (400, 422)


# ---------- Chat ----------
class TestChat:
    @pytest.fixture(scope="class")
    def session_id(self):
        return f"test_session_{uuid.uuid4().hex[:10]}"

    def test_chat_message(self, session, session_id):
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

    def test_chat_history(self, session, session_id):
        # Allow a moment for persistence
        time.sleep(1)
        r = session.get(f"{API}/chat/history/{session_id}", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data["session_id"] == session_id
        msgs = data["messages"]
        assert isinstance(msgs, list)
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles
        for m in msgs:
            assert "_id" not in m

    def test_chat_lead_create_and_list(self, session, session_id):
        payload = {
            "name": "TEST_Lead",
            "email": f"lead_{uuid.uuid4().hex[:6]}@example.com",
            "company": "TEST_Co",
            "phone": "+26771",
            "inquiry_type": "Corporate Training",
            "session_id": session_id,
            "notes": "TEST_notes",
        }
        r = session.post(f"{API}/chat/lead", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        lead = r.json()
        assert lead["name"] == payload["name"]
        assert lead["email"] == payload["email"]
        assert "id" in lead and "created_at" in lead

        r2 = session.get(f"{API}/chat/leads", timeout=20)
        assert r2.status_code == 200
        items = r2.json()
        assert isinstance(items, list)
        for it in items[:5]:
            assert "_id" not in it
        assert lead["id"] in [i["id"] for i in items]
