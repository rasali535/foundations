import bcrypt
import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

from server import app, USERS_DB, RATE_LIMIT_STORE


@pytest.mark.asyncio
async def test_persistent_therapist_staff_login_restores_role_and_therapist_scope():
    RATE_LIMIT_STORE.clear()
    USERS_DB.clear()

    db = AsyncMongoMockClient()["test_foundations_db"]
    app.state.db = db

    password = "test-therapist-password"
    await db.staff_users.insert_one({
        "user_id": "therapist@example.com",
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Test Therapist",
        "therapist_id": "therapist-test-id",
        "organisation_id": None,
        "active": True,
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={
            "username": "THERAPIST@EXAMPLE.COM",
            "password": password,
        })
        assert login.status_code == 200
        data = login.json()
        assert data["role"] == "therapist"
        assert data["therapist_id"] == "therapist-test-id"
        assert data["organisation_id"] is None

        me = await ac.get("/api/me")
        assert me.status_code == 200
        me_data = me.json()
        assert me_data["role"] == "therapist"
        assert me_data["therapist_id"] == "therapist-test-id"


@pytest.mark.asyncio
async def test_inactive_staff_login_is_rejected():
    RATE_LIMIT_STORE.clear()
    USERS_DB.clear()

    db = AsyncMongoMockClient()["test_foundations_db_inactive"]
    app.state.db = db

    await db.staff_users.insert_one({
        "user_id": "inactive@example.com",
        "password_hash": bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
        "role": "therapist",
        "name": "Inactive Therapist",
        "therapist_id": "inactive-id",
        "active": False,
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={
            "username": "inactive@example.com",
            "password": "password123",
        })
        assert login.status_code == 401
