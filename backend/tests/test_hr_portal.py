import pytest
import pytest_asyncio
import bcrypt
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from server import app, USERS_DB, RATE_LIMIT_STORE
from models import (
    Therapist, Organisation, OrganisationUser, CRMClient, Booking,
    HR_MIN_REPORTING_COUNT
)
from services.therapist_service import DEFAULT_THERAPISTS

FORBIDDEN_PII_KEYS = {
    "first_name", "last_name", "full_name", "client_name", "email", "phone",
    "client_id", "client_number", "intake_id", "participant_id", "therapist_id",
    "therapist_name", "booking_id", "reason_for_seeking_therapy", "clinical", "triage_level"
}

def scan_dict_for_pii(obj, path=""):
    """Recursively checks that no forbidden client PII or clinical keys exist in JSON object."""
    findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if k.lower() in FORBIDDEN_PII_KEYS:
                findings.append(f"Forbidden PII key found: '{current_path}'")
            findings.extend(scan_dict_for_pii(v, current_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            findings.extend(scan_dict_for_pii(item, f"{path}[{idx}]"))
    return findings


@pytest_asyncio.fixture
async def hr_test_app():
    RATE_LIMIT_STORE.clear()
    client = AsyncMongoMockClient()
    mock_db = client["test_foundations_db"]

    # Seed Default Therapists
    for t in DEFAULT_THERAPISTS:
        await mock_db.therapists.insert_one(Therapist(**t).model_dump())

    app.state.db = mock_db

    # Clear and seed basic system users
    USERS_DB.clear()
    USERS_DB["admin"] = {
        "password_hash": bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "FCA Operations Admin",
        "therapist_id": None
    }

    return app, mock_db


@pytest.mark.asyncio
async def test_hr_authentication_and_scoping(hr_test_app):
    """Verify admin provisions organisations and HR accounts; HR users are permanently scoped on login."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Admin login
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass123"})

        # 2. Admin creates Organisation A
        res_a = await ac.post("/api/admin-ops/organisations", json={
            "name": "Letshego Financial Holdings",
            "code": "LETS",
            "contract_start": "2026-01-01",
            "contract_end": "2026-12-31",
            "allocated_sessions": 300,
            "contact_person": "Tshepo Modise",
            "contact_email": "hr@letshego.com"
        })
        assert res_a.status_code == 201
        org_a_id = res_a.json()["id"]

        # 3. Admin creates Organisation B
        res_b = await ac.post("/api/admin-ops/organisations", json={
            "name": "Stanbic Bank Botswana",
            "code": "STAN",
            "contract_start": "2026-06-01",
            "contract_end": "2027-05-31",
            "allocated_sessions": 150
        })
        assert res_b.status_code == 201
        org_b_id = res_b.json()["id"]

        # 4. Admin creates HR user for Org A
        res_user_a = await ac.post(f"/api/admin-ops/organisations/{org_a_id}/users", json={
            "username": "letshego_hr",
            "password": "hrpass12345",
            "email": "hr.lead@letshego.com",
            "name": "Tshepo Modise",
            "role": "hr_admin"
        })
        assert res_user_a.status_code == 201
        assert res_user_a.json()["organisation_id"] == org_a_id

        # 5. Admin creates HR user for Org B
        res_user_b = await ac.post(f"/api/admin-ops/organisations/{org_b_id}/users", json={
            "username": "stanbic_hr",
            "password": "hrpass67890",
            "email": "wellness@stanbic.com",
            "name": "Neo Morake",
            "role": "hr_viewer"
        })
        assert res_user_b.status_code == 201
        assert res_user_b.json()["organisation_id"] == org_b_id

    # 6. HR User A logs in
    async with AsyncClient(transport=transport, base_url="http://test") as hr_client_a:
        login_a = await hr_client_a.post("/api/login", json={"username": "letshego_hr", "password": "hrpass12345"})
        assert login_a.status_code == 200
        assert login_a.json()["role"] == "hr_admin"
        assert login_a.json()["organisation_id"] == org_a_id

        # Check /api/hr/me
        me_a = await hr_client_a.get("/api/hr/me")
        assert me_a.status_code == 200
        assert me_a.json()["organisation_id"] == org_a_id
        assert me_a.json()["organisation_name"] == "Letshego Financial Holdings"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_cross_tenant_block(hr_test_app):
    """Verify HR User A cannot access Org B aggregates through parameter tampering."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    # Setup Org A & Org B
    await mock_db.organisations.insert_one(Organisation(id="org-a", name="Organisation A", code="ORGA").model_dump())
    await mock_db.organisations.insert_one(Organisation(id="org-b", name="Organisation B", code="ORGB").model_dump())

    USERS_DB["hr_user_a"] = {
        "password_hash": bcrypt.hashpw(b"passA", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR A",
        "organisation_id": "org-a",
        "therapist_id": None
    }
    USERS_DB["hr_user_b"] = {
        "password_hash": bcrypt.hashpw(b"passB", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR B",
        "organisation_id": "org-b",
        "therapist_id": None
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "hr_user_a", "password": "passA"})

        # Normal access to own org
        res_own = await ac.get("/api/hr/dashboard")
        assert res_own.status_code == 200
        assert res_own.json()["organisation_id"] == "org-a"
        assert res_own.json()["organisation_name"] == "Organisation A"

        # Tampering attempt with query param ?organisation_id=org-b -> MUST BE 403
        res_tamper = await ac.get("/api/hr/dashboard?organisation_id=org-b")
        assert res_tamper.status_code == 403
        assert "Cross-tenant access forbidden" in res_tamper.json()["detail"]


@pytest.mark.asyncio
async def test_aggregate_metrics_and_contract_calculations(hr_test_app):
    """Verify accurate aggregation of session types, modes, attendance, and contract utilisation."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-corp-01"
    await mock_db.organisations.insert_one(Organisation(
        id=org_id,
        name="Botswana Telecommunications",
        code="BTC",
        contract_start="2026-01-01",
        contract_end="2026-12-31",
        allocated_sessions=200
    ).model_dump())

    USERS_DB["btc_hr"] = {
        "password_hash": bcrypt.hashpw(b"btcpass", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "BTC Wellness",
        "organisation_id": org_id,
        "therapist_id": None
    }

    # Create 3 clients belonging to this org
    client1 = CRMClient(id="client-01", first_name="Synthetic", last_name="One", email="s1@btc.co.bw", phone="+26771111111", client_number="FCA-001", organisation_id=org_id)
    client2 = CRMClient(id="client-02", first_name="Synthetic", last_name="Two", email="s2@btc.co.bw", phone="+26772222222", client_number="FCA-002", organisation_id=org_id)
    # Individual client NOT belonging to this org
    client3 = CRMClient(id="client-03", first_name="Private", last_name="Client", email="priv@gmail.com", phone="+26773333333", client_number="FCA-003", organisation_id=None)

    await mock_db.crm_clients.insert_one(client1.model_dump())
    await mock_db.crm_clients.insert_one(client2.model_dump())
    await mock_db.crm_clients.insert_one(client3.model_dump())

    # Create 8 bookings for client1 and client2 (All in 2026-09)
    # 5 Completed, 2 Confirmed, 1 Cancelled
    # 6 Individual, 2 Couple
    # 5 In-Person, 3 Virtual
    bookings_data = [
        # Client 1
        {"client_id": "client-01", "therapist_id": "therapist-caroline-sithole", "session_type": "individual", "session_mode": "in_person", "status": "completed", "starts_at": "2026-09-02T08:00:00Z", "ends_at": "2026-09-02T09:00:00Z"},
        {"client_id": "client-01", "therapist_id": "therapist-caroline-sithole", "session_type": "individual", "session_mode": "in_person", "status": "completed", "starts_at": "2026-09-09T08:00:00Z", "ends_at": "2026-09-09T09:00:00Z"},
        {"client_id": "client-01", "therapist_id": "therapist-alpheaus-chiwaze", "session_type": "individual", "session_mode": "virtual", "status": "completed", "starts_at": "2026-09-16T14:00:00Z", "ends_at": "2026-09-16T15:00:00Z"},
        {"client_id": "client-01", "therapist_id": "therapist-alpheaus-chiwaze", "session_type": "couple", "session_mode": "virtual", "status": "completed", "starts_at": "2026-09-23T14:00:00Z", "ends_at": "2026-09-23T15:00:00Z"},
        {"client_id": "client-01", "therapist_id": "therapist-caroline-sithole", "session_type": "individual", "session_mode": "in_person", "status": "confirmed", "starts_at": "2026-09-30T08:00:00Z", "ends_at": "2026-09-30T09:00:00Z"},
        # Client 2
        {"client_id": "client-02", "therapist_id": "therapist-caroline-sithole", "session_type": "individual", "session_mode": "in_person", "status": "completed", "starts_at": "2026-09-05T10:00:00Z", "ends_at": "2026-09-05T11:00:00Z"},
        {"client_id": "client-02", "therapist_id": "therapist-alpheaus-chiwaze", "session_type": "individual", "session_mode": "virtual", "status": "confirmed", "starts_at": "2026-09-12T11:00:00Z", "ends_at": "2026-09-12T12:00:00Z"},
        {"client_id": "client-02", "therapist_id": "therapist-caroline-sithole", "session_type": "couple", "session_mode": "in_person", "status": "cancelled", "starts_at": "2026-09-19T10:00:00Z", "ends_at": "2026-09-19T11:00:00Z"},
        # Private Client (MUST NOT be counted in BTC metrics)
        {"client_id": "client-03", "therapist_id": "therapist-caroline-sithole", "session_type": "individual", "session_mode": "in_person", "status": "completed", "starts_at": "2026-09-01T08:00:00Z", "ends_at": "2026-09-01T09:00:00Z"},
    ]

    for bd in bookings_data:
        await mock_db.bookings.insert_one(Booking(**bd).model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "btc_hr", "password": "btcpass"})

        dash_res = await ac.get("/api/hr/dashboard?period=current_month")
        assert dash_res.status_code == 200
        data = dash_res.json()

        # Total sessions for BTC = 8 (Private client omitted)
        assert data["total_sessions"]["count"] == 8
        assert data["total_sessions"]["display"] == "8"
        assert data["total_sessions"]["suppressed"] is False

        # Completed sessions = 5 (>= 5, displayed exactly)
        assert data["completed"]["count"] == 5
        assert data["completed"]["display"] == "5"

        # Cancelled sessions = 1 (< 5, MUST BE SUPPRESSED)
        assert data["cancelled"]["count"] is None
        assert data["cancelled"]["display"] == "<5"
        assert data["cancelled"]["suppressed"] is True

        # Session Types: Individual = 6 (>= 5), Couple = 2 (< 5, suppressed)
        assert data["session_types"]["individual"]["count"] == 6
        assert data["session_types"]["couple"]["display"] == "<5"
        assert data["session_types"]["couple"]["suppressed"] is True

        # Contract: Allocated 200, Used 7 (5 completed + 2 confirmed), Remaining 193, Utilisation = 3.5%
        assert data["contract"]["allocated_sessions"] == 200
        assert data["contract"]["sessions_used"] == 7
        assert data["contract"]["sessions_remaining"] == 193
        assert data["contract"]["utilisation_percentage"] == 3.5


@pytest.mark.asyncio
async def test_privacy_threshold_suppression_comprehensive(hr_test_app):
    """Verify privacy threshold masking across dashboard, session types, session modes, and utilisation trends."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-small"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Small Startup Ltd", code="SML").model_dump())
    USERS_DB["small_hr"] = {
        "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        "role": "hr_viewer",
        "name": "HR Small",
        "organisation_id": org_id,
        "therapist_id": None
    }

    # 1 client with only 3 sessions (< 5 total)
    client = CRMClient(id="client-small", first_name="A", last_name="B", email="a@sml.com", phone="+26771111000", client_number="FCA-SML", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    for i in range(3):
        b = Booking(
            client_id="client-small",
            therapist_id="therapist-caroline-sithole",
            session_type="individual",
            session_mode="in_person",
            status="completed",
            starts_at=f"2026-09-0{i+1}T08:00:00Z",
            ends_at=f"2026-09-0{i+1}T09:00:00Z"
        )
        await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "small_hr", "password": "pass"})

        # Dashboard: Total sessions = 3 < 5 -> suppressed
        dash = await ac.get("/api/hr/dashboard")
        assert dash.status_code == 200
        assert dash.json()["total_sessions"]["display"] == "<5"
        assert dash.json()["total_sessions"]["suppressed"] is True

        # Session Types: individual = 3 < 5 -> suppressed
        st = await ac.get("/api/hr/session-types")
        assert st.status_code == 200
        assert st.json()["types"]["individual"]["metric"]["display"] == "<5"
        assert st.json()["types"]["individual"]["metric"]["suppressed"] is True

        # Utilisation Trends: 2026-09 has 3 sessions -> suppressed
        trends = await ac.get("/api/hr/utilisation")
        assert trends.status_code == 200
        point = trends.json()["trends"][0]
        assert point["total_sessions"]["display"] == "<5"
        assert point["total_sessions"]["suppressed"] is True


@pytest.mark.asyncio
async def test_raw_crm_and_clinical_access_blocked_for_hr_users(hr_test_app):
    """Verify that authenticated HR users receive 403 Forbidden on all raw CRM, clinical, and booking endpoints."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-test"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Test Corp", code="TC").model_dump())
    USERS_DB["hr_user"] = {
        "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR User",
        "organisation_id": org_id,
        "therapist_id": None
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "hr_user", "password": "pass"})

        # 1. CRM Clients Directory -> 403
        res = await ac.get("/api/crm/clients")
        assert res.status_code == 403

        # 2. Specific CRM Client Detail -> 403
        res = await ac.get("/api/crm/clients/dummy-client-id")
        assert res.status_code == 403

        # 3. CRM Notes -> 403
        res = await ac.post("/api/crm/clients/dummy-client-id/notes", json={"content": "Illegal HR note"})
        assert res.status_code == 403

        # 4. Clinical Intake Records -> 403
        res = await ac.get("/api/clinical/records")
        assert res.status_code == 403

        res_client_intakes = await ac.get("/api/crm/clients/dummy-client-id/intakes")
        assert res_client_intakes.status_code == 403

        # 5. Raw Bookings List -> 403
        res = await ac.get("/api/bookings")
        assert res.status_code == 403

        # 6. Therapists Directory -> 403
        res = await ac.get("/api/therapists")
        assert res.status_code == 403

        # 7. Admin Ops Audit Logs -> 403
        res = await ac.get("/api/admin-ops/audit/logs")
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_pii_scanner_across_all_hr_endpoints(hr_test_app):
    """Automated security scan: verify that NO /api/hr/* endpoint leaks any client PII or clinical fields."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-pii-scan"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Scanner Corp", code="SCAN", allocated_sessions=100).model_dump())
    USERS_DB["hr_scanner"] = {
        "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Scanner",
        "organisation_id": org_id,
        "therapist_id": None
    }

    # Add client and booking
    client = CRMClient(id="client-pii", first_name="TopSecretFirst", last_name="ConfidentialLast", email="secret@corp.com", phone="+26779999999", client_number="FCA-SECRET", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())
    booking = Booking(client_id="client-pii", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at="2026-09-01T08:00:00Z", ends_at="2026-09-01T09:00:00Z")
    await mock_db.bookings.insert_one(booking.model_dump())

    hr_endpoints = [
        "/api/hr/me",
        "/api/hr/dashboard",
        "/api/hr/contract",
        "/api/hr/utilisation",
        "/api/hr/session-types",
        "/api/hr/session-modes"
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "hr_scanner", "password": "pass"})

        for endpoint in hr_endpoints:
            res = await ac.get(endpoint)
            assert res.status_code == 200, f"Endpoint {endpoint} failed with {res.status_code}"
            json_data = res.json()

            # Run recursive PII scan
            findings = scan_dict_for_pii(json_data)
            assert len(findings) == 0, f"PII leak detected on {endpoint}: {findings}"

            # String dump scan for actual client sensitive values
            raw_text = res.text
            assert "TopSecretFirst" not in raw_text
            assert "ConfidentialLast" not in raw_text
            assert "secret@corp.com" not in raw_text
            assert "+26779999999" not in raw_text
            assert "FCA-SECRET" not in raw_text
            assert "client-pii" not in raw_text


@pytest.mark.asyncio
async def test_safe_aggregate_csv_export_and_audit_logging(hr_test_app):
    """Verify aggregate-only CSV export and audit logging with zero client PII."""
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-export"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Export Corp", code="EXP").model_dump())
    USERS_DB["hr_exporter"] = {
        "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Exporter",
        "organisation_id": org_id,
        "therapist_id": None
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "hr_exporter", "password": "pass"})

        # Export CSV
        csv_res = await ac.get("/api/hr/export/csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        csv_text = csv_res.text
        assert "Period,Total Sessions,Completed,Cancelled,No Show" in csv_text
        assert "Client Name" not in csv_text
        assert "Booking ID" not in csv_text

        # Verify Audit Log
        logs = await mock_db.crm_activity_log.find({"actor_user_id": "hr_exporter"}).to_list(10)
        actions = [l["action"] for l in logs]
        assert "hr_report_exported" in actions
        for l in logs:
            assert l["metadata"].get("organisation_id") == org_id
            assert "client_id" not in l["metadata"]
            assert "first_name" not in str(l)
