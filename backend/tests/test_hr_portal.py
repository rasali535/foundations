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

        # Attendance: Cancelled = 1 (< 5), Completed = 5
        # Complementary suppression protects Cancelled from being derived via 8 - 5 - 2 (confirmed) = 1
        assert data["cancelled"]["count"] is None
        assert data["cancelled"]["display"] == "<5"
        assert data["cancelled"]["suppressed"] is True
        assert data["completed"]["count"] is None
        assert data["completed"]["display"] == "<5"
        assert data["completed"]["suppressed"] is True

        # Session Types: Individual = 6, Couple = 2 (< 5).
        # Complementary suppression protects Couple from being derived via 8 - 6 - 0 = 2
        assert data["session_types"]["couple"]["display"] == "<5"
        assert data["session_types"]["couple"]["count"] is None
        assert data["session_types"]["couple"]["percentage"] is None
        assert data["session_types"]["couple"]["suppressed"] is True
        assert data["session_types"]["individual"]["display"] == "<5"
        assert data["session_types"]["individual"]["count"] is None
        assert data["session_types"]["individual"]["percentage"] is None
        assert data["session_types"]["individual"]["suppressed"] is True

        # Session Modes: 5 In-Person, 3 Virtual (< 5).
        # Two-category rule: Both are suppressed to prevent derivation
        assert data["session_modes"]["virtual"]["display"] == "<5"
        assert data["session_modes"]["virtual"]["count"] is None
        assert data["session_modes"]["virtual"]["percentage"] is None
        assert data["session_modes"]["in_person"]["display"] == "<5"
        assert data["session_modes"]["in_person"]["count"] is None
        assert data["session_modes"]["in_person"]["percentage"] is None

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


@pytest.mark.asyncio
async def test_privacy_case_a_session_type_complementary_suppression(hr_test_app):
    """
    Case A: Total = 7, Individual = 5, Couple = 2, Family = 0.
    Expected: Couple = 2 must not be derivable via Total - Individual - Family.
    Individual and Couple must both be suppressed (<5, count=None, percentage=None).
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-a"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case A Corp", code="CS-A").model_dump())
    USERS_DB["user_case_a"] = {
        "password_hash": bcrypt.hashpw(b"passA", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case A",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-a", first_name="Synthetic", last_name="A", email="a@casea.com", phone="+26771000001", client_number="FCA-A", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # 5 Individual, 2 Couple, 0 Family
    for i in range(5):
        b = Booking(client_id="client-case-a", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-09-0{i+1}T08:00:00Z", ends_at=f"2026-09-0{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())
    for i in range(2):
        b = Booking(client_id="client-case-a", therapist_id="therapist-caroline-sithole", session_type="couple", session_mode="in_person", status="completed", starts_at=f"2026-09-1{i+1}T08:00:00Z", ends_at=f"2026-09-1{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_a", "password": "passA"})

        dash_res = await ac.get("/api/hr/dashboard?period=current_month")
        assert dash_res.status_code == 200
        dash = dash_res.json()

        assert dash["total_sessions"]["count"] == 7
        assert dash["total_sessions"]["display"] == "7"

        # Complementary suppression: Couple (<5) must NOT be derivable from Total (7) - Individual (5)
        # Therefore, Individual MUST ALSO be suppressed
        st = dash["session_types"]
        assert st["couple"]["display"] == "<5"
        assert st["couple"]["count"] is None
        assert st["couple"]["percentage"] is None
        assert st["couple"]["suppressed"] is True

        assert st["individual"]["display"] == "<5"
        assert st["individual"]["count"] is None
        assert st["individual"]["percentage"] is None
        assert st["individual"]["suppressed"] is True

        assert st["family"]["display"] == "0"
        assert st["family"]["count"] == 0
        assert st["family"]["suppressed"] is False

        # Endpoint /api/hr/session-types must return identical protection
        types_res = await ac.get("/api/hr/session-types")
        assert types_res.status_code == 200
        t_data = types_res.json()["types"]
        assert t_data["couple"]["metric"]["display"] == "<5"
        assert t_data["couple"]["metric"]["count"] is None
        assert t_data["couple"]["percentage"] is None
        assert t_data["individual"]["metric"]["display"] == "<5"
        assert t_data["individual"]["metric"]["count"] is None
        assert t_data["individual"]["percentage"] is None


@pytest.mark.asyncio
async def test_privacy_case_b_session_mode_two_category_suppression(hr_test_app):
    """
    Case B: Total = 10, In-Person = 8, Virtual = 2.
    Expected: In a 2-category breakdown, exposing one side exposes the other side (10 - 8 = 2).
    Both sides must be suppressed (<5, count=None, percentage=None).
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-b"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case B Corp", code="CS-B").model_dump())
    USERS_DB["user_case_b"] = {
        "password_hash": bcrypt.hashpw(b"passB", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case B",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-b", first_name="Synthetic", last_name="B", email="b@caseb.com", phone="+26771000002", client_number="FCA-B", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # 8 In-Person, 2 Virtual
    for i in range(8):
        b = Booking(client_id="client-case-b", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-09-0{i+1}T08:00:00Z" if i < 9 else "2026-09-10T08:00:00Z", ends_at="2026-09-10T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())
    for i in range(2):
        b = Booking(client_id="client-case-b", therapist_id="therapist-alpheaus-chiwaze", session_type="individual", session_mode="virtual", status="completed", starts_at=f"2026-09-2{i+1}T08:00:00Z", ends_at="2026-09-21T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_b", "password": "passB"})

        dash_res = await ac.get("/api/hr/dashboard?period=current_month")
        assert dash_res.status_code == 200
        dash = dash_res.json()

        assert dash["total_sessions"]["count"] == 10
        sm = dash["session_modes"]

        # Neither mode may be exposed to reveal the other
        assert sm["virtual"]["display"] == "<5"
        assert sm["virtual"]["count"] is None
        assert sm["virtual"]["percentage"] is None
        assert sm["virtual"]["suppressed"] is True

        assert sm["in_person"]["display"] == "<5"
        assert sm["in_person"]["count"] is None
        assert sm["in_person"]["percentage"] is None
        assert sm["in_person"]["suppressed"] is True

        modes_res = await ac.get("/api/hr/session-modes")
        assert modes_res.status_code == 200
        m_data = modes_res.json()["modes"]
        assert m_data["virtual"]["metric"]["display"] == "<5"
        assert m_data["virtual"]["percentage"] is None
        assert m_data["in_person"]["metric"]["display"] == "<5"
        assert m_data["in_person"]["percentage"] is None


@pytest.mark.asyncio
async def test_privacy_case_c_attendance_breakdown_inference_protection(hr_test_app):
    """
    Case C: Total = 12, Completed = 9, Cancelled = 2, No Show = 1.
    Expected: Small attendance buckets (<5) are protected against inference.
    Completed must be complementarily suppressed to protect Cancelled + No Show from tight bounding.
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-c"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case C Corp", code="CS-C").model_dump())
    USERS_DB["user_case_c"] = {
        "password_hash": bcrypt.hashpw(b"passC", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case C",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-c", first_name="Synthetic", last_name="C", email="c@casec.com", phone="+26771000003", client_number="FCA-C", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # 9 Completed, 2 Cancelled, 1 No-Show
    for i in range(9):
        b = Booking(client_id="client-case-c", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-09-0{i+1}T08:00:00Z" if i < 9 else "2026-09-10T08:00:00Z", ends_at="2026-09-10T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())
    for i in range(2):
        b = Booking(client_id="client-case-c", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="cancelled", starts_at=f"2026-09-1{i+1}T08:00:00Z", ends_at="2026-09-11T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())
    b = Booking(client_id="client-case-c", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="no_show", starts_at="2026-09-25T08:00:00Z", ends_at="2026-09-25T09:00:00Z")
    await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_c", "password": "passC"})

        dash_res = await ac.get("/api/hr/dashboard?period=current_month")
        assert dash_res.status_code == 200
        dash = dash_res.json()

        assert dash["total_sessions"]["count"] == 12

        # Cancelled and No-Show are < 5, their sum is 3 (< 5).
        # Completed must be complementarily suppressed to protect them.
        assert dash["completed"]["display"] == "<5"
        assert dash["completed"]["count"] is None
        assert dash["completed"]["percentage"] is None
        assert dash["completed"]["suppressed"] is True

        assert dash["cancelled"]["display"] == "<5"
        assert dash["cancelled"]["count"] is None
        assert dash["cancelled"]["percentage"] is None
        assert dash["cancelled"]["suppressed"] is True

        assert dash["no_show"]["display"] == "<5"
        assert dash["no_show"]["count"] is None
        assert dash["no_show"]["percentage"] is None
        assert dash["no_show"]["suppressed"] is True


@pytest.mark.asyncio
async def test_privacy_case_d_time_series_longitudinal_privacy(hr_test_app):
    """
    Case D: January = 8, February = 2, Quarter Total = 10.
    Expected: February exact value must not be derivable from Quarter Total - January.
    In the monthly utilisation trends, both January and February must be suppressed (<5, count=None).
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-d"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case D Corp", code="CS-D").model_dump())
    USERS_DB["user_case_d"] = {
        "password_hash": bcrypt.hashpw(b"passD", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case D",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-d", first_name="Synthetic", last_name="D", email="d@cased.com", phone="+26771000004", client_number="FCA-D", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # 8 sessions in 2026-01
    for i in range(8):
        b = Booking(client_id="client-case-d", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-01-0{i+1}T08:00:00Z", ends_at=f"2026-01-0{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())
    # 2 sessions in 2026-02
    for i in range(2):
        b = Booking(client_id="client-case-d", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-02-0{i+1}T08:00:00Z", ends_at=f"2026-02-0{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_d", "password": "passD"})

        trends_res = await ac.get("/api/hr/utilisation?granularity=monthly")
        assert trends_res.status_code == 200
        trends = trends_res.json()["trends"]

        assert len(trends) == 2
        jan = next(t for t in trends if t["period"] == "2026-01")
        feb = next(t for t in trends if t["period"] == "2026-02")

        # February (2) is < 5; January (8) must be complementarily suppressed so Feb is not derivable
        assert feb["total_sessions"]["display"] == "<5"
        assert feb["total_sessions"]["count"] is None
        assert feb["total_sessions"]["suppressed"] is True

        assert jan["total_sessions"]["display"] == "<5"
        assert jan["total_sessions"]["count"] is None
        assert jan["total_sessions"]["suppressed"] is True


@pytest.mark.asyncio
async def test_privacy_case_e_api_payload_inspection_zero_hidden_raw_counts(hr_test_app):
    """
    Case E: Inspect browser API JSON.
    Expected: Suppressed field strictly contains count: null, percentage: null, suppressed: true.
    Exact hidden count must NOT exist anywhere in the JSON response under any alias.
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-e"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case E Corp", code="CS-E").model_dump())
    USERS_DB["user_case_e"] = {
        "password_hash": bcrypt.hashpw(b"passE", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case E",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-e", first_name="E", last_name="E", email="e@casee.com", phone="+26771000005", client_number="FCA-E", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # Create 3 sessions (all suppressed)
    for i in range(3):
        b = Booking(client_id="client-case-e", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-09-0{i+1}T08:00:00Z", ends_at=f"2026-09-0{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())

    def verify_no_hidden_raw_counts(obj):
        if isinstance(obj, dict):
            # Check prohibited keys
            prohibited_keys = {"raw_count", "actual_count", "actual", "hidden_count", "real_count", "unmasked"}
            for k in obj.keys():
                assert k.lower() not in prohibited_keys, f"Found leaked raw key: {k}"
            # If suppressed, count and percentage MUST be None
            if obj.get("suppressed") is True:
                assert obj.get("count") is None, f"Suppressed object contains non-null count: {obj}"
                assert obj.get("percentage") is None, f"Suppressed object contains non-null percentage: {obj}"
                assert obj.get("display") == "<5"
            for v in obj.values():
                verify_no_hidden_raw_counts(v)
        elif isinstance(obj, list):
            for item in obj:
                verify_no_hidden_raw_counts(item)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_e", "password": "passE"})

        for ep in ["/api/hr/dashboard", "/api/hr/utilisation", "/api/hr/session-types", "/api/hr/session-modes"]:
            res = await ac.get(ep)
            assert res.status_code == 200
            json_payload = res.json()
            verify_no_hidden_raw_counts(json_payload)


@pytest.mark.asyncio
async def test_privacy_case_f_csv_export_strict_privacy_policy(hr_test_app):
    """
    Case F: CSV export.
    Expected: No suppressed raw values. Output contains '<5' for all suppressed metrics.
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-case-f"
    await mock_db.organisations.insert_one(Organisation(id=org_id, name="Case F Corp", code="CS-F").model_dump())
    USERS_DB["user_case_f"] = {
        "password_hash": bcrypt.hashpw(b"passF", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Case F",
        "organisation_id": org_id,
        "therapist_id": None
    }

    client = CRMClient(id="client-case-f", first_name="F", last_name="F", email="f@casef.com", phone="+26771000006", client_number="FCA-F", organisation_id=org_id)
    await mock_db.crm_clients.insert_one(client.model_dump())

    # 3 sessions in 2026-09 (< 5 total)
    for i in range(3):
        b = Booking(client_id="client-case-f", therapist_id="therapist-caroline-sithole", session_type="individual", session_mode="in_person", status="completed", starts_at=f"2026-09-0{i+1}T08:00:00Z", ends_at=f"2026-09-0{i+1}T09:00:00Z")
        await mock_db.bookings.insert_one(b.model_dump())

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_case_f", "password": "passF"})

        csv_res = await ac.get("/api/hr/export/csv")
        assert csv_res.status_code == 200
        csv_text = csv_res.text
        lines = csv_text.strip().split("\n")
        assert len(lines) == 2
        header = lines[0]
        row = lines[1]
        assert header == "Period,Total Sessions,Completed,Cancelled,No Show"
        # All columns must be suppressed as <5, NEVER returning 3 or 0
        assert row == "2026-09,<5,<5,<5,<5"


@pytest.mark.asyncio
async def test_direct_identifier_attack_and_tenant_isolation(hr_test_app):
    """
    Tenant isolation & direct identifier attack test.
    HR User A attempts:
      - ?organisation_id=org-b -> 403
      - ?org_id=org-b -> 403
      - header organisation_id: org-b -> 403
      - header x-organisation-id: org-b -> 403
      - header organisation: org-b -> 403
      - self-registration -> 404 / 405 (endpoint does not exist)
      - modifying own organisation_id or role -> 403
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    await mock_db.organisations.insert_one(Organisation(id="org-alpha", name="Corp Alpha", code="ALPHA").model_dump())
    await mock_db.organisations.insert_one(Organisation(id="org-beta", name="Corp Beta", code="BETA").model_dump())

    USERS_DB["user_alpha"] = {
        "password_hash": bcrypt.hashpw(b"passAlpha", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Alpha",
        "organisation_id": "org-alpha",
        "therapist_id": None
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "user_alpha", "password": "passAlpha"})

        # Attack 1: Query param ?organisation_id=org-beta -> 403
        r1 = await ac.get("/api/hr/dashboard?organisation_id=org-beta")
        assert r1.status_code == 403
        assert "Cross-tenant access forbidden" in r1.json()["detail"]

        # Attack 2: Query param ?org_id=org-beta -> 403
        r2 = await ac.get("/api/hr/dashboard?org_id=org-beta")
        assert r2.status_code == 403

        # Attack 3: Header organisation_id: org-beta -> 403
        r3 = await ac.get("/api/hr/dashboard", headers={"organisation_id": "org-beta"})
        assert r3.status_code == 403

        # Attack 4: Header x-organisation-id: org-beta -> 403
        r4 = await ac.get("/api/hr/dashboard", headers={"x-organisation-id": "org-beta"})
        assert r4.status_code == 403

        # Attack 5: Header organisation: org-beta -> 403
        r5 = await ac.get("/api/hr/dashboard", headers={"organisation": "org-beta"})
        assert r5.status_code == 403

        # Attack 6: Attempt public HR registration -> endpoint does not exist (404/405)
        r6 = await ac.post("/api/hr/register", json={"username": "hacker", "password": "pwd"})
        assert r6.status_code in [404, 405]

        # Attack 7: Attempt modifying organisation through admin-ops -> 403 Forbidden
        r7 = await ac.patch("/api/admin-ops/organisations/org-alpha", json={"name": "Hacked Org"})
        assert r7.status_code == 403

        r8 = await ac.post("/api/admin-ops/organisations/org-beta/users", json={"username": "hacker", "password": "pwd", "email": "h@b.com", "name": "H", "role": "hr_admin"})
        assert r8.status_code == 403


@pytest.mark.asyncio
async def test_organisation_contact_data_privacy(hr_test_app):
    """
    Verify /api/hr/me and /api/hr/contract do not leak FCA internal contacts or other corporate contacts.
    """
    test_app, mock_db = hr_test_app
    transport = ASGITransport(app=test_app)

    org_id = "org-contact-check"
    await mock_db.organisations.insert_one(Organisation(
        id=org_id,
        name="Private Holdings",
        code="PRIV",
        contact_person="Internal FCA Handler",
        contact_email="fca.internal.staff@academyfoundations.com",
        allocated_sessions=50
    ).model_dump())

    USERS_DB["hr_contact_test"] = {
        "password_hash": bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode(),
        "role": "hr_admin",
        "name": "HR Private",
        "organisation_id": org_id,
        "therapist_id": None
    }

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "hr_contact_test", "password": "pass"})

        me_res = await ac.get("/api/hr/me")
        assert me_res.status_code == 200
        me_json = me_res.json()
        assert "contact_person" not in me_json
        assert "contact_email" not in me_json
        assert "fca.internal.staff" not in me_res.text

        contract_res = await ac.get("/api/hr/contract")
        assert contract_res.status_code == 200
        contract_json = contract_res.json()
        assert "contact_person" not in contract_json
        assert "contact_email" not in contract_json
        assert "fca.internal.staff" not in contract_res.text
