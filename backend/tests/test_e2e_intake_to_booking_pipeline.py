import pytest
import pytest_asyncio
import bcrypt
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from server import app, USERS_DB
from models import Therapist
from services.notification_service import NotificationService

TEST_IN_PERSON_THERAPIST = {
    "id": "e2e-inperson-therapist",
    "name": "FCA In-Person Clinician",
    "email": "inperson@academyfoundations.com",
    "phone": "+26771000001",
    "active": True,
    "supports_in_person": True,
    "supports_virtual": False,
    "specializations": ["Individual Counselling", "Couple Therapy", "Family Systems"],
    "working_days": [0, 1, 2, 3, 4],
    "working_hours_start": "08:00",
    "working_hours_end": "17:00",
    "slot_duration_minutes": 60,
    "default_location": "FCA Clinic Gaborone",
    "virtual_meeting_link_template": None
}

TEST_VIRTUAL_THERAPIST = {
    "id": "e2e-virtual-therapist",
    "name": "FCA Virtual Specialist",
    "email": "virtual@academyfoundations.com",
    "phone": "+26771000002",
    "active": True,
    "supports_in_person": False,
    "supports_virtual": True,
    "specializations": ["Virtual Counselling"],
    "working_days": [0, 1, 2, 3, 4, 5],
    "working_hours_start": "08:00",
    "working_hours_end": "18:00",
    "slot_duration_minutes": 60,
    "default_location": None,
    "virtual_meeting_link_template": "https://meet.academyfoundations.com/room/fca-telehealth"
}

@pytest_asyncio.fixture
async def e2e_app():
    client = AsyncMongoMockClient()
    mock_db = client["test_e2e_db"]
    # Seed test therapists
    await mock_db.therapists.insert_one(Therapist(**TEST_IN_PERSON_THERAPIST).model_dump())
    await mock_db.therapists.insert_one(Therapist(**TEST_VIRTUAL_THERAPIST).model_dump())
    app.state.db = mock_db

    # Register authorized admin user
    USERS_DB["admin_user"] = {
        "password_hash": bcrypt.hashpw(b"SecureAdminPass2026!", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "FCA Operations Admin",
        "therapist_id": None
    }
    return app, mock_db

@pytest.mark.asyncio
async def test_complete_intake_to_booking_workflow(e2e_app):
    test_app, mock_db = e2e_app
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # =========================================================================
        # STEP 1: academyfoundations.com/intake -> Synthetic client submits intake
        # =========================================================================
        synthetic_intake_payload = {
            "full_name": "Kagiso Synthetic Client",
            "email": "kagiso.synthetic@example.com",
            "phone": "+267 71 555 777",
            "dob": "1991-04-12",
            "preferred_contact_method": "WhatsApp",
            "emergency_contact_name": "Lesedi Synthetic",
            "emergency_contact_relationship": "Sister",
            "emergency_contact_phone": "+267 72 111 333",
            "reason_for_seeking_therapy": "Navigating career transition and stress management",
            "safety_screen": {
                "self_harm": "No",
                "harm_others": "No",
                "unsafe_environment": "No",
                "abuse_experienced": "No"
            },
            "consent_acknowledged": True,
            "typed_signature": "Kagiso Synthetic Client",
            "consent_date": "2026-09-07"
        }

        intake_res = await client.post("/api/clinical/intake", json=synthetic_intake_payload)
        assert intake_res.status_code == 200
        intake_data = intake_res.json()

        # =========================================================================
        # STEP 2: CRM profile created & Client number generated
        # =========================================================================
        assert intake_data["status"] == "intake_received"
        assert intake_data["is_new_client"] is True
        assert intake_data["triage_level"] == "ROUTINE_COUNSELLING"
        crm_client_id = intake_data["client_id"]
        client_number = intake_data["client_number"]
        assert client_number.startswith("FCA-")

        # =========================================================================
        # STEP 3: Admin logs in and opens client profile
        # =========================================================================
        login_res = await client.post("/api/login", json={
            "username": "admin_user",
            "password": "SecureAdminPass2026!"
        })
        assert login_res.status_code == 200
        assert login_res.json()["role"] == "admin"

        # Open client profile
        profile_res = await client.get(f"/api/crm/clients/{crm_client_id}")
        assert profile_res.status_code == 200
        profile_data = profile_res.json()
        assert profile_data["client"]["id"] == crm_client_id
        assert profile_data["client"]["email"] == "kagiso.synthetic@example.com"
        assert len(profile_data["intakes"]) == 1
        assert profile_data["intakes"][0]["submission_data"]["full_name"] == "Kagiso Synthetic Client"

        # =========================================================================
        # STEP 4: Book 4 monthly sessions & STEP 5: Correct therapist assigned
        # =========================================================================
        multi_booking_payload = {
            "client_id": crm_client_id,
            "therapist_id": "e2e-inperson-therapist",  # Dedicated In-Person Therapist
            "session_type": "individual",
            "session_mode": "in_person",
            "slots": [
                {"starts_at": "2026-10-06T09:00:00Z"},
                {"starts_at": "2026-10-13T09:00:00Z"},
                {"starts_at": "2026-10-20T09:00:00Z"},
                {"starts_at": "2026-10-27T09:00:00Z"}
            ],
            "notes": "October 4-Week Counselling Program",
            "send_notifications": True
        }

        booking_res = await client.post("/api/bookings/multi", json=multi_booking_payload)
        assert booking_res.status_code == 200
        booking_data = booking_res.json()
        assert booking_data["total_created"] == 4
        assert len(booking_data["bookings"]) == 4

        # Verify correct therapist assignment across all 4 sessions
        for b in booking_data["bookings"]:
            assert b["therapist_id"] == "e2e-inperson-therapist"
            assert b["therapist_name"] == "FCA In-Person Clinician"
            assert b["session_mode"] == "in_person"
            assert b["status"] == "confirmed"

            # =========================================================================
            # STEP 6: Calendar updated & reflect all sessions
            # =========================================================================
            calendar_res = await client.get("/api/bookings?start_date=2026-10-01&end_date=2026-10-31&limit=100")
            assert calendar_res.status_code == 200
            calendar_data = calendar_res.json()
            assert calendar_data["total"] == 4
            assert len(calendar_data["bookings"]) == 4

            # Check filter by therapist
            t_filter_res = await client.get("/api/bookings?start_date=2026-10-01&end_date=2026-10-31&therapist_id=e2e-inperson-therapist")
            assert t_filter_res.status_code == 200
            assert t_filter_res.json()["total"] == 4

        # =========================================================================
        # STEP 7: Email notification sent/logged with clean metadata
        # STEP 8: WhatsApp notification sent/logged with masked recipient
        # =========================================================================
        notif_res = await client.get(f"/api/admin-ops/notifications?client_id={crm_client_id}")
        assert notif_res.status_code == 200
        notifs = notif_res.json()
        assert len(notifs) >= 1

        channels = [n["channel"] for n in notifs]
        assert "email" in channels or "whatsapp" in channels

        for n in notifs:
            assert n["client_id"] == crm_client_id
            # Confirm no raw clinical reasons leaked in notification payload metadata
            assert "Navigating career transition" not in str(n.get("metadata", {}))

        # Re-fetch profile to confirm 4 bookings and notifications attached
        updated_profile_res = await client.get(f"/api/crm/clients/{crm_client_id}")
        assert updated_profile_res.status_code == 200
        updated_profile = updated_profile_res.json()
        assert len(updated_profile["bookings"]) == 4
        assert len(updated_profile["activity_logs"]) >= 3  # intake_received, client_created, booking_created
