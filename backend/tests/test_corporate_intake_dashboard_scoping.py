import pytest
from mongomock_motor import AsyncMongoMockClient

from models import Organisation
from services.intake_service import IntakeService
from services.hr_service import HRReportingService


@pytest.mark.asyncio
async def test_corporate_intake_link_scopes_clients_to_respective_dashboard():
    client = AsyncMongoMockClient()
    db = client["test_foundations_db"]

    org_a = Organisation(id="org-a", name="Organisation A", code="ORGA")
    org_b = Organisation(id="org-b", name="Organisation B", code="ORGB")
    await db.organisations.insert_many([org_a.model_dump(), org_b.model_dump()])

    # Corporate A link: must attach only to Organisation A.
    result_a = await IntakeService.process_intake_submission(
        db,
        {
            "first_name": "Alice",
            "last_name": "A",
            "email": "alice.a@example.com",
            "phone": "+26770000001",
            "organisation_code": "ORGA",
        },
        source="website_intake",
    )
    assert result_a["source_type"] == "corporate"
    assert result_a["organisation"]["id"] == "org-a"

    # Corporate B link: must attach only to Organisation B.
    result_b = await IntakeService.process_intake_submission(
        db,
        {
            "first_name": "Bob",
            "last_name": "B",
            "email": "bob.b@example.com",
            "phone": "+26770000002",
            "organisation_code": "ORGB",
        },
        source="website_intake",
    )
    assert result_b["source_type"] == "corporate"
    assert result_b["organisation"]["id"] == "org-b"

    # Public/private intake must remain outside all corporate dashboards.
    result_private = await IntakeService.process_intake_submission(
        db,
        {
            "first_name": "Private",
            "last_name": "Client",
            "email": "private@example.com",
            "phone": "+26770000003",
        },
        source="website_intake",
    )
    assert result_private["source_type"] == "private"
    assert result_private["organisation"] is None

    client_a = await db.crm_clients.find_one({"id": result_a["client_id"]}, {"_id": 0})
    client_b = await db.crm_clients.find_one({"id": result_b["client_id"]}, {"_id": 0})
    client_private = await db.crm_clients.find_one({"id": result_private["client_id"]}, {"_id": 0})

    assert client_a["organisation_id"] == "org-a"
    assert client_b["organisation_id"] == "org-b"
    assert client_private.get("organisation_id") is None

    dashboard_a_clients = await HRReportingService._get_org_client_ids(db, "org-a")
    dashboard_b_clients = await HRReportingService._get_org_client_ids(db, "org-b")

    assert result_a["client_id"] in dashboard_a_clients
    assert result_a["client_id"] not in dashboard_b_clients

    assert result_b["client_id"] in dashboard_b_clients
    assert result_b["client_id"] not in dashboard_a_clients

    assert result_private["client_id"] not in dashboard_a_clients
    assert result_private["client_id"] not in dashboard_b_clients


@pytest.mark.asyncio
async def test_existing_private_client_moves_to_corporate_dashboard_only_when_using_valid_link():
    client = AsyncMongoMockClient()
    db = client["test_foundations_db"]

    org = Organisation(id="org-a", name="Organisation A", code="ORGA")
    await db.organisations.insert_one(org.model_dump())

    private = await IntakeService.process_intake_submission(
        db,
        {
            "first_name": "Existing",
            "last_name": "Client",
            "email": "existing@example.com",
            "phone": "+26770000004",
        },
        source="website_intake",
    )
    assert private["source_type"] == "private"

    corporate = await IntakeService.process_intake_submission(
        db,
        {
            "first_name": "Existing",
            "last_name": "Client",
            "email": "existing@example.com",
            "phone": "+26770000004",
            "organisation_code": "ORGA",
        },
        source="website_intake",
    )
    assert corporate["client_id"] == private["client_id"]

    dashboard_clients = await HRReportingService._get_org_client_ids(db, "org-a")
    assert private["client_id"] in dashboard_clients

    stored = await db.crm_clients.find_one({"id": private["client_id"]}, {"_id": 0})
    assert stored["organisation_id"] == "org-a"
    assert stored["organisation_name"] == "Organisation A"
