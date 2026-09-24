import bcrypt
import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from server import app, USERS_DB, RATE_LIMIT_STORE


@pytest.fixture
def deletion_db():
    RATE_LIMIT_STORE.clear()
    USERS_DB.clear()
    db = AsyncMongoMockClient()["test_super_admin_deletion"]
    app.state.db = db
    return db


def seed_user(username, password, role, name):
    USERS_DB[username] = {
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": role,
        "name": name,
        "therapist_id": None,
        "organisation_id": None,
    }


@pytest.mark.asyncio
async def test_only_super_admin_can_delete_hr_user(deletion_db):
    db = deletion_db
    seed_user("super", "superpass", "super_admin", "Super")
    seed_user("admin", "adminpass", "admin", "Admin")

    await db.organisations.insert_one({"id": "org-1", "name": "Org One", "code": "ORG1"})
    await db.organisation_users.insert_one({
        "id": "hr-account-1",
        "organisation_id": "org-1",
        "user_id": "hr@example.com",
        "name": "HR User",
        "role": "hr_admin",
        "password_hash": "placeholder",
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "adminpass"})
        denied = await ac.delete("/api/admin-ops/organisations/org-1/users/hr-account-1")
        assert denied.status_code == 403

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "super", "password": "superpass"})
        deleted = await ac.delete("/api/admin-ops/organisations/org-1/users/hr-account-1")
        assert deleted.status_code == 200
        assert await db.organisation_users.count_documents({"id": "hr-account-1"}) == 0


@pytest.mark.asyncio
async def test_super_admin_cascade_deletes_organisation_operational_records(deletion_db):
    db = deletion_db
    seed_user("super", "superpass", "super_admin", "Super")

    await db.organisations.insert_one({"id": "org-1", "name": "Org One", "code": "ORG1"})
    await db.organisation_users.insert_one({
        "id": "hr-1", "organisation_id": "org-1", "user_id": "hr@org.test",
        "name": "HR", "role": "hr_admin", "password_hash": "placeholder"
    })
    await db.organisation_contacts.insert_one({
        "id": "contact-1", "organisation_id": "org-1", "email": "employee@org.test"
    })
    await db.crm_clients.insert_one({
        "id": "client-1", "organisation_id": "org-1", "first_name": "Employee"
    })
    await db.bookings.insert_one({
        "id": "booking-1", "client_id": "client-1", "status": "completed"
    })
    await db.crm_intake_submissions.insert_one({
        "id": "intake-1", "client_id": "client-1"
    })
    await db.invoices.insert_one({
        "id": "invoice-1", "organisation_id": "org-1", "status": "issued"
    })
    await db.invoice_items.insert_one({
        "id": "item-1", "invoice_id": "invoice-1"
    })
    await db.invoice_booking_links.insert_one({
        "id": "link-1", "invoice_id": "invoice-1", "booking_id": "booking-1"
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "super", "password": "superpass"})

        blocked = await ac.delete("/api/admin-ops/organisations/org-1")
        assert blocked.status_code == 409

        deleted = await ac.delete("/api/admin-ops/organisations/org-1?cascade=true")
        assert deleted.status_code == 200

    assert await db.organisations.count_documents({"id": "org-1"}) == 0
    assert await db.organisation_users.count_documents({"organisation_id": "org-1"}) == 0
    assert await db.organisation_contacts.count_documents({"organisation_id": "org-1"}) == 0
    assert await db.crm_clients.count_documents({"organisation_id": "org-1"}) == 0
    assert await db.bookings.count_documents({"client_id": "client-1"}) == 0
    assert await db.crm_intake_submissions.count_documents({"client_id": "client-1"}) == 0
    assert await db.invoices.count_documents({"organisation_id": "org-1"}) == 0
    assert await db.invoice_items.count_documents({"invoice_id": "invoice-1"}) == 0
    assert await db.invoice_booking_links.count_documents({"invoice_id": "invoice-1"}) == 0

    audit = await db.crm_activity_log.find_one({"action": "organisation_deleted"})
    assert audit is not None
    assert audit["metadata"]["organisation_id"] == "org-1"


@pytest.mark.asyncio
async def test_staff_delete_protects_self_and_last_super_admin(deletion_db):
    db = deletion_db
    seed_user("super@example.com", "superpass", "super_admin", "Super")

    password_hash = bcrypt.hashpw(b"superpass", bcrypt.gensalt()).decode()
    await db.staff_users.insert_one({
        "user_id": "super@example.com",
        "password_hash": password_hash,
        "role": "super_admin",
        "name": "Super",
        "active": True,
    })
    await db.staff_users.insert_one({
        "user_id": "admin@example.com",
        "password_hash": bcrypt.hashpw(b"adminpass", bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "Admin",
        "active": True,
    })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "super@example.com", "password": "superpass"})

        self_delete = await ac.delete("/api/admin-ops/staff-users/super%40example.com")
        assert self_delete.status_code == 400

        admin_delete = await ac.delete("/api/admin-ops/staff-users/admin%40example.com")
        assert admin_delete.status_code == 200
        assert await db.staff_users.count_documents({"user_id": "admin@example.com"}) == 0
