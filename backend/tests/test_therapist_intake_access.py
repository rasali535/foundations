import pytest
import pytest_asyncio
import bcrypt
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from server import app, USERS_DB, RATE_LIMIT_STORE
from models import Therapist
from services.therapist_service import DEFAULT_THERAPISTS

@pytest_asyncio.fixture
async def test_app():
    """Inject mock database with DEFAULT_THERAPISTS and test user accounts into app state."""
    RATE_LIMIT_STORE.clear()
    client = AsyncMongoMockClient()
    mock_db = client["test_foundations_db"]

    # Seed Default Therapists (Caroline Sithole & Alpheaus Chiwaze)
    for t in DEFAULT_THERAPISTS:
        await mock_db.therapists.insert_one(Therapist(**t).model_dump())
    
    app.state.db = mock_db

    # Seed test users into USERS_DB
    USERS_DB["admin"] = {
        "password_hash": bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "Clinical Administrator",
        "therapist_id": None
    }
    USERS_DB["caroline"] = {
        "password_hash": bcrypt.hashpw(b"carolinepass123", bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Caroline Sithole",
        "therapist_id": "therapist-caroline-sithole"
    }
    USERS_DB["alpheaus"] = {
        "password_hash": bcrypt.hashpw(b"alpheauspass123", bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Alpheaus Chiwaze",
        "therapist_id": "therapist-alpheaus-chiwaze"
    }
    USERS_DB["staff"] = {
        "password_hash": bcrypt.hashpw(b"staffpass123", bcrypt.gensalt()).decode(),
        "role": "staff",
        "name": "Front Desk Staff",
        "therapist_id": None
    }

    return app


@pytest.mark.asyncio
async def test_therapist_configurations(test_app):
    """Verify Caroline Sithole and Alpheaus Chiwaze capabilities and temporary Mon-Fri 08:00-17:00 schedules."""
    db = test_app.state.db
    therapists = await db.therapists.find({}).to_list(10)
    assert len(therapists) >= 2

    caroline = next((t for t in therapists if t["name"] == "Caroline Sithole"), None)
    assert caroline is not None, "Caroline Sithole must exist in therapists"
    assert caroline["supports_in_person"] is True
    assert caroline["supports_virtual"] is False
    assert caroline["working_days"] == [0, 1, 2, 3, 4]
    assert caroline["working_hours_start"] == "08:00"
    assert caroline["working_hours_end"] == "17:00"
    assert caroline["slot_duration_minutes"] == 60

    alpheaus = next((t for t in therapists if t["name"] == "Alpheaus Chiwaze"), None)
    assert alpheaus is not None, "Alpheaus Chiwaze must exist in therapists"
    assert alpheaus["supports_in_person"] is False
    assert alpheaus["supports_virtual"] is True
    assert alpheaus["working_days"] == [0, 1, 2, 3, 4]
    assert alpheaus["working_hours_start"] == "08:00"
    assert alpheaus["working_hours_end"] == "17:00"
    assert alpheaus["slot_duration_minutes"] == 60


@pytest.mark.asyncio
async def test_capability_routing_and_rejection(test_app):
    """Verify Caroline accepts in-person and rejects virtual; Alpheaus accepts virtual and rejects in-person."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login as Admin
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # Create Client
        c_res = await ac.post("/api/crm/clients", json={
            "first_name": "Kagiso",
            "last_name": "Molefe",
            "email": "kagiso.molefe@example.com",
            "phone": "+26771112233"
        })
        assert c_res.status_code == 200
        client_id = c_res.json()["id"]

        # 1. Caroline + In-Person -> SUCCESS
        c_in_person = await ac.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-caroline-sithole",
            "session_type": "individual",
            "session_mode": "in_person",
            "starts_at": "2026-10-05T08:00:00Z",
            "send_notifications": False
        })
        assert c_in_person.status_code == 200
        assert c_in_person.json()["therapist_id"] == "therapist-caroline-sithole"
        assert c_in_person.json()["session_mode"] == "in_person"

        # 2. Caroline + Virtual -> REJECTED (400 Bad Request)
        c_virtual = await ac.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-caroline-sithole",
            "session_type": "individual",
            "session_mode": "virtual",
            "starts_at": "2026-10-06T08:00:00Z",
            "send_notifications": False
        })
        assert c_virtual.status_code == 400
        assert "does not support virtual" in c_virtual.json()["detail"].lower()

        # 3. Alpheaus + Virtual -> SUCCESS
        a_virtual = await ac.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-alpheaus-chiwaze",
            "session_type": "individual",
            "session_mode": "virtual",
            "starts_at": "2026-10-07T08:00:00Z",
            "send_notifications": False
        })
        assert a_virtual.status_code == 200
        assert a_virtual.json()["therapist_id"] == "therapist-alpheaus-chiwaze"
        assert a_virtual.json()["session_mode"] == "virtual"
        assert a_virtual.json()["virtual_meeting_link"] is not None

        # 4. Alpheaus + In-Person -> REJECTED (400 Bad Request)
        a_in_person = await ac.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-alpheaus-chiwaze",
            "session_type": "individual",
            "session_mode": "in_person",
            "starts_at": "2026-10-08T08:00:00Z",
            "send_notifications": False
        })
        assert a_in_person.status_code == 400
        assert "does not support in-person" in a_in_person.json()["detail"].lower()


@pytest.mark.asyncio
async def test_four_session_monthly_bookings(test_app):
    """Verify booking 4 monthly sessions with Caroline (in-person) and 4 with Alpheaus (virtual)."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # Client 1 for Caroline
        c1_res = await ac.post("/api/crm/clients", json={
            "first_name": "Lesego",
            "last_name": "Tau",
            "email": "lesego.tau@example.com",
            "phone": "+26772223344"
        })
        c1_id = c1_res.json()["id"]

        # Multi-booking request for Caroline (4 Mondays)
        caroline_multi = await ac.post("/api/bookings/multi", json={
            "client_id": c1_id,
            "therapist_id": "therapist-caroline-sithole",
            "session_type": "individual",
            "session_mode": "in_person",
            "slots": [
                {"starts_at": "2026-10-05T08:00:00Z"},
                {"starts_at": "2026-10-12T08:00:00Z"},
                {"starts_at": "2026-10-19T08:00:00Z"},
                {"starts_at": "2026-10-26T08:00:00Z"}
            ],
            "send_notifications": False
        })
        assert caroline_multi.status_code == 200
        assert len(caroline_multi.json()["bookings"]) == 4

        # Client 2 for Alpheaus
        c2_res = await ac.post("/api/crm/clients", json={
            "first_name": "Tebogo",
            "last_name": "Khumalo",
            "email": "tebogo.khumalo@example.com",
            "phone": "+26773334455"
        })
        c2_id = c2_res.json()["id"]

        # Multi-booking request for Alpheaus (4 Tuesdays)
        alpheaus_multi = await ac.post("/api/bookings/multi", json={
            "client_id": c2_id,
            "therapist_id": "therapist-alpheaus-chiwaze",
            "session_type": "individual",
            "session_mode": "virtual",
            "slots": [
                {"starts_at": "2026-10-06T14:00:00Z"},
                {"starts_at": "2026-10-13T14:00:00Z"},
                {"starts_at": "2026-10-20T14:00:00Z"},
                {"starts_at": "2026-10-27T14:00:00Z"}
            ],
            "send_notifications": False
        })
        assert alpheaus_multi.status_code == 200
        assert len(alpheaus_multi.json()["bookings"]) == 4


@pytest.mark.asyncio
async def test_therapist_intake_access_authorization_matrix(test_app):
    """Verify strict access control: assigned therapist=200, unassigned=403, staff=403, anon=401, admin=200."""
    transport = ASGITransport(app=test_app)

    # 1. Public client submits intake form
    async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
        intake_res = await anon_client.post("/api/clinical/intake", json={
            "full_name": "Mpho Motsepe",
            "email": "mpho.motsepe@example.com",
            "phone": "+267 74 445 566",
            "dob": "1992-04-12",
            "emergency_contact_name": "Lerato Motsepe",
            "emergency_contact_relationship": "Sister",
            "emergency_contact_phone": "+267 71 222 333",
            "reason_for_seeking_therapy": "Work-life balance and stress management.",
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "No"
            },
            "consent_acknowledged": True,
            "typed_signature": "Mpho Motsepe",
            "consent_date": "2026-09-07"
        })
        assert intake_res.status_code == 200
        client_id = intake_res.json()["client_id"]
        intake_id = intake_res.json()["intake_id"]

        # Anonymous access to client intake -> 401 Unauthorized
        anon_intakes = await anon_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert anon_intakes.status_code == 401

        anon_single_intake = await anon_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert anon_single_intake.status_code == 401

    # 2. Caroline before booking assignment -> 403 Forbidden
    async with AsyncClient(transport=transport, base_url="http://test") as caroline_client:
        await caroline_client.post("/api/login", json={"username": "caroline", "password": "carolinepass123"})
        
        # Profile view before assignment -> 403
        c_prof = await caroline_client.get(f"/api/crm/clients/{client_id}")
        assert c_prof.status_code == 403

        # Intakes list before assignment -> 403
        c_intakes = await caroline_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert c_intakes.status_code == 403

        # Single intake before assignment -> 403
        c_single = await caroline_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert c_single.status_code == 403

    # 3. Admin assigns Caroline to Mpho
    async with AsyncClient(transport=transport, base_url="http://test") as admin_client:
        await admin_client.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        
        book_res = await admin_client.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-caroline-sithole",
            "session_type": "individual",
            "session_mode": "in_person",
            "starts_at": "2026-10-05T11:00:00Z",
            "send_notifications": False
        })
        assert book_res.status_code == 200

        # Admin can view client intake -> 200
        admin_intakes = await admin_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert admin_intakes.status_code == 200
        assert len(admin_intakes.json()) == 1

        admin_single = await admin_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert admin_single.status_code == 200

    # 4. Caroline AFTER booking assignment -> 200 OK
    async with AsyncClient(transport=transport, base_url="http://test") as caroline_client:
        await caroline_client.post("/api/login", json={"username": "caroline", "password": "carolinepass123"})

        # Caroline views profile -> 200
        c_prof = await caroline_client.get(f"/api/crm/clients/{client_id}")
        assert c_prof.status_code == 200
        assert c_prof.json()["client"]["first_name"] == "Mpho"

        # Caroline views intakes list -> 200
        c_intakes = await caroline_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert c_intakes.status_code == 200
        assert len(c_intakes.json()) == 1

        # Caroline views single intake -> 200
        c_single = await caroline_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert c_single.status_code == 200
        assert c_single.json()["id"] == intake_id
        assert c_single.json()["submission_data"]["reason_for_seeking_therapy"] == "Work-life balance and stress management."

    # 5. Alpheaus is UNASSIGNED to Mpho -> 403 Forbidden
    async with AsyncClient(transport=transport, base_url="http://test") as alpheaus_client:
        await alpheaus_client.post("/api/login", json={"username": "alpheaus", "password": "alpheauspass123"})

        a_prof = await alpheaus_client.get(f"/api/crm/clients/{client_id}")
        assert a_prof.status_code == 403

        a_intakes = await alpheaus_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert a_intakes.status_code == 403

        a_single = await alpheaus_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert a_single.status_code == 403

    # 6. Staff Role -> 403 Forbidden on clinical intake endpoints
    async with AsyncClient(transport=transport, base_url="http://test") as staff_client:
        await staff_client.post("/api/login", json={"username": "staff", "password": "staffpass123"})

        s_intakes = await staff_client.get(f"/api/crm/clients/{client_id}/intakes")
        assert s_intakes.status_code == 403

        s_single = await staff_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert s_single.status_code == 403


@pytest.mark.asyncio
async def test_intake_viewing_audit_trail_logging(test_app):
    """Verify that viewing an intake creates an audit log with action='intake_viewed' and ZERO clinical data in metadata."""
    transport = ASGITransport(app=test_app)
    db = test_app.state.db

    # Submit intake
    async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
        intake_res = await anon_client.post("/api/clinical/intake", json={
            "full_name": "Naledi Gaolathe",
            "email": "naledi.gaolathe@example.com",
            "phone": "+267 75 556 677",
            "dob": "1995-02-18",
            "emergency_contact_name": "Lesego Gaolathe",
            "emergency_contact_relationship": "Brother",
            "emergency_contact_phone": "+267 72 333 444",
            "reason_for_seeking_therapy": "TOP_SECRET_CLINICAL_DETAILS_CONFIDENTIAL",
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "No"
            },
            "consent_acknowledged": True,
            "typed_signature": "Naledi Gaolathe",
            "consent_date": "2026-09-07"
        })
        assert intake_res.status_code == 200
        client_id = intake_res.json()["client_id"]
        intake_id = intake_res.json()["intake_id"]

    # Assign Caroline
    async with AsyncClient(transport=transport, base_url="http://test") as admin_client:
        await admin_client.post("/api/login", json={"username": "admin", "password": "adminpass123"})
        await admin_client.post("/api/bookings", json={
            "client_id": client_id,
            "therapist_id": "therapist-caroline-sithole",
            "session_type": "individual",
            "session_mode": "in_person",
            "starts_at": "2026-10-05T14:00:00Z",
            "send_notifications": False
        })

    # Clear prior logs
    await db.crm_activity_log.delete_many({"action": "intake_viewed"})

    # Caroline accesses the intake record
    async with AsyncClient(transport=transport, base_url="http://test") as caroline_client:
        await caroline_client.post("/api/login", json={"username": "caroline", "password": "carolinepass123"})
        view_res = await caroline_client.get(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert view_res.status_code == 200

    # Verify audit log in DB
    logs = await db.crm_activity_log.find({"client_id": client_id, "action": "intake_viewed"}).to_list(10)
    assert len(logs) == 1
    log = logs[0]
    assert log["actor_user_id"] == "caroline"
    assert log["client_id"] == client_id
    assert log["metadata"] == {"intake_id": intake_id}

    # CRITICAL: Confirm zero clinical text in metadata or log content
    assert "TOP_SECRET" not in str(log)
    assert "CONFIDENTIAL" not in str(log)
    assert "reason" not in log["metadata"]


@pytest.mark.asyncio
async def test_intake_immutability(test_app):
    """Verify that intake submissions cannot be modified or deleted via HTTP methods."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # Submit intake
        intake_res = await ac.post("/api/clinical/intake", json={
            "full_name": "Kabo Moloi",
            "email": "kabo.moloi@example.com",
            "phone": "+267 76 667 788",
            "dob": "1991-08-14",
            "emergency_contact_name": "Goitse Moloi",
            "emergency_contact_relationship": "Parent",
            "emergency_contact_phone": "+267 73 444 555",
            "reason_for_seeking_therapy": "Test immutability",
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "No"
            },
            "consent_acknowledged": True,
            "typed_signature": "Kabo Moloi",
            "consent_date": "2026-09-07"
        })
        assert intake_res.status_code == 200
        client_id = intake_res.json()["client_id"]
        intake_id = intake_res.json()["intake_id"]

        # PUT -> 405 Method Not Allowed
        put_res = await ac.put(f"/api/crm/clients/{client_id}/intakes/{intake_id}", json={"reason": "Modified"})
        assert put_res.status_code == 405

        # PATCH -> 405 Method Not Allowed
        patch_res = await ac.patch(f"/api/crm/clients/{client_id}/intakes/{intake_id}", json={"reason": "Modified"})
        assert patch_res.status_code == 405

        # DELETE -> 405 Method Not Allowed
        delete_res = await ac.delete(f"/api/crm/clients/{client_id}/intakes/{intake_id}")
        assert delete_res.status_code == 405
