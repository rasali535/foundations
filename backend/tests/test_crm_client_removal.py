import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from server import app, USERS_DB


def add_user(username, password, role):
    USERS_DB[username] = {
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": role,
        "name": username,
        "therapist_id": None,
        "organisation_id": None,
    }


@pytest.mark.asyncio
async def test_crm_client_removal_requires_super_admin():
    db = AsyncMongoMockClient()["crm_remove_auth"]
    app.state.db = db
    USERS_DB.clear()
    add_user("admin", "pass", "admin")
    await db.crm_clients.insert_one({"id": "c1", "client_number": "FCA-1"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "admin", "password": "pass"})
        response = await ac.delete("/api/crm/clients/c1")

    assert response.status_code == 403
    assert await db.crm_clients.count_documents({"id": "c1"}) == 1


@pytest.mark.asyncio
async def test_super_admin_removes_client_operational_records():
    db = AsyncMongoMockClient()["crm_remove_success"]
    app.state.db = db
    USERS_DB.clear()
    add_user("super", "pass", "super_admin")

    await db.crm_clients.insert_one({"id": "c1", "client_number": "FCA-1"})
    await db.crm_intake_submissions.insert_one({"id": "i1", "client_id": "c1"})
    await db.crm_notes.insert_one({"id": "n1", "client_id": "c1"})
    await db.bookings.insert_one({"id": "b1", "client_id": "c1"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "super", "password": "pass"})
        response = await ac.delete("/api/crm/clients/c1")

    assert response.status_code == 200
    assert await db.crm_clients.count_documents({"id": "c1"}) == 0
    assert await db.crm_intake_submissions.count_documents({"client_id": "c1"}) == 0
    assert await db.crm_notes.count_documents({"client_id": "c1"}) == 0
    assert await db.bookings.count_documents({"client_id": "c1"}) == 0
    assert await db.crm_activity_log.count_documents({"action": "crm_client_deleted"}) == 1


@pytest.mark.asyncio
async def test_invoiced_client_cannot_be_removed():
    db = AsyncMongoMockClient()["crm_remove_invoice_guard"]
    app.state.db = db
    USERS_DB.clear()
    add_user("super", "pass", "super_admin")

    await db.crm_clients.insert_one({"id": "c1", "client_number": "FCA-1"})
    await db.bookings.insert_one({"id": "b1", "client_id": "c1", "active_invoice_id": "inv1"})
    await db.invoices.insert_one({"id": "inv1", "status": "draft"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/login", json={"username": "super", "password": "pass"})
        response = await ac.delete("/api/crm/clients/c1")

    assert response.status_code == 409
    assert await db.crm_clients.count_documents({"id": "c1"}) == 1
