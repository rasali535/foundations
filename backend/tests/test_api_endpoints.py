import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from server import app, USERS_DB
from services.therapist_service import TherapistService

@pytest_asyncio.fixture
async def test_app():
    # Inject mock database into app state
    client = AsyncMongoMockClient()
    mock_db = client["test_foundations_db"]
    await TherapistService.seed_defaults_if_empty(mock_db)
    app.state.db = mock_db
    return app

# ==================== Security & Unauthenticated API Access Tests ====================
@pytest.mark.asyncio
async def test_unauthenticated_api_access_blocked(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Access CRM clients without session -> 401
        res = await ac.get("/api/crm/clients")
        assert res.status_code == 401
        assert "Authentication required" in res.text

        # 2. Access Bookings without session -> 401
        res = await ac.get("/api/bookings")
        assert res.status_code == 401

        # 3. Access Therapists without session -> 401
        res = await ac.get("/api/therapists")
        assert res.status_code == 401

        # 4. Access Audit Logs without session -> 401
        res = await ac.get("/api/admin-ops/audit/logs")
        assert res.status_code == 401

# ==================== Public Intake Endpoint Direct Submission ====================
@pytest.mark.asyncio
async def test_public_intake_creates_crm_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        intake_payload = {
            "full_name": "Kabo Modise",
            "email": "kabo.modise@example.com",
            "phone": "+267 71 888 999",
            "dob": "1988-11-20",
            "preferred_contact_method": "WhatsApp",
            "emergency_contact_name": "Naledi Modise",
            "emergency_contact_relationship": "Sister",
            "emergency_contact_phone": "+267 72 000 111",
            "reason_for_seeking_therapy": "Anxiety management",
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "No"
            },
            "consent_acknowledged": True,
            "typed_signature": "Kabo Modise",
            "consent_date": "2026-09-07"
        }

        res = await ac.post("/api/clinical/intake", json=intake_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "intake_received"
        assert data["is_new_client"] is True
        assert data["triage_level"] == "ROUTINE_COUNSELLING"
        assert "client_number" in data
        assert data["client_number"].startswith("FCA-")

        # Second intake from same client (e.g. follow-up)
        intake_payload2 = intake_payload.copy()
        intake_payload2["reason_for_seeking_therapy"] = "Session 2 check-in"
        res2 = await ac.post("/api/clinical/intake", json=intake_payload2)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["is_new_client"] is False
        assert data2["client_id"] == data["client_id"]

# ==================== Full Authenticated Workflow ====================
@pytest.mark.asyncio
async def test_authenticated_admin_workflow(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Login as admin
        login_res = await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        assert login_res.status_code == 200
        user_info = login_res.json()
        assert user_info["role"] == "admin"

        # 2. Check /api/me
        me_res = await ac.get("/api/me")
        assert me_res.status_code == 200
        assert me_res.json()["user_id"] == "admin"

        # 3. Create client manually
        client_res = await ac.post("/api/crm/clients", json={
            "first_name": "Lesedi",
            "last_name": "Tawana",
            "email": "lesedi.tawana@example.com",
            "phone": "+267 76 123 456",
            "preferred_contact_method": "Phone call"
        })
        assert client_res.status_code == 200
        client = client_res.json()
        client_id = client["id"]

        # 4. Add CRM Note
        note_res = await ac.post(f"/api/crm/clients/{client_id}/notes", json={
            "content": "Administrative note: Client requested WhatsApp reminders.",
            "is_pinned": True
        })
        assert note_res.status_code == 200
        note = note_res.json()
        assert note["is_pinned"] is True

        # 5. Create Monthly Multi-Booking (4 slots)
        multi_res = await ac.post("/api/bookings/multi", json={
            "client_id": client_id,
            "session_type": "individual",
            "session_mode": "in_person",
            "slots": [
                {"starts_at": "2026-11-02T09:00:00Z"},
                {"starts_at": "2026-11-09T09:00:00Z"},
                {"starts_at": "2026-11-16T09:00:00Z"},
                {"starts_at": "2026-11-23T09:00:00Z"}
            ],
            "notes": "November monthly package",
            "send_notifications": False
        })
        assert multi_res.status_code == 200
        multi_data = multi_res.json()
        assert multi_data["total_created"] == 4
        created_bookings = multi_data["bookings"]

        # 6. Reschedule slot 1
        b1_id = created_bookings[0]["id"]
        reschedule_res = await ac.post(f"/api/bookings/{b1_id}/reschedule", json={
            "new_starts_at": "2026-11-02T11:00:00Z",
            "reason": "Admin schedule adjustment",
            "send_notifications": False
        })
        assert reschedule_res.status_code == 200
        assert reschedule_res.json()["starts_at"] == "2026-11-02T11:00:00+00:00"

        # 7. Cancel slot 2
        b2_id = created_bookings[1]["id"]
        status_res = await ac.post(f"/api/bookings/{b2_id}/status", json={
            "status": "cancelled",
            "cancellation_reason": "Client unavailable",
            "send_notifications": False
        })
        assert status_res.status_code == 200
        assert status_res.json()["status"] == "cancelled"

        # 8. Fetch Client Profile and confirm all linked entities
        profile_res = await ac.get(f"/api/crm/clients/{client_id}")
        assert profile_res.status_code == 200
        profile = profile_res.json()
        assert profile["client"]["id"] == client_id
        assert len(profile["bookings"]) == 4
        assert len(profile["notes"]) == 1
        assert len(profile["activity_logs"]) >= 4

        # 9. Check Dashboard KPIs
        dash_res = await ac.get("/api/crm/dashboard")
        assert dash_res.status_code == 200
        kpis = dash_res.json()["kpis"]
        assert kpis["total_clients"] >= 1
        assert kpis["cancellations_count"] >= 1
