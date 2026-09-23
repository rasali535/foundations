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


@pytest.mark.asyncio
async def test_me_rehydrates_persistent_user_after_process_cache_reset():
    RATE_LIMIT_STORE.clear()
    USERS_DB.clear()

    db = AsyncMongoMockClient()["test_foundations_db_rehydrate"]
    app.state.db = db

    password = "persisted-password"
    await db.staff_users.insert_one({
        "user_id": "Admin.MixedCase@Example.com",
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "Persistent Admin",
        "therapist_id": None,
        "organisation_id": None,
        "active": True,
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={
            "username": "admin.mixedcase@example.com",
            "password": password,
        })
        assert login.status_code == 200

        # Simulate a new Render worker/process where the in-memory cache is empty
        # while the browser still has a valid signed session cookie.
        USERS_DB.clear()

        me = await ac.get("/api/me")
        assert me.status_code == 200
        payload = me.json()
        assert payload["user_id"] == "admin.mixedcase@example.com"
        assert payload["role"] == "admin"
        assert payload["name"] == "Persistent Admin"


@pytest.mark.asyncio
async def test_login_case_insensitive_against_persistent_user_id():
    RATE_LIMIT_STORE.clear()
    USERS_DB.clear()

    db = AsyncMongoMockClient()["test_foundations_db_casefold"]
    app.state.db = db

    password = "casefold-password"
    await db.staff_users.insert_one({
        "user_id": "Mixed.Case.Admin",
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "Mixed Case Admin",
        "active": True,
    })

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login = await ac.post("/api/login", json={
            "username": "MIXED.CASE.ADMIN",
            "password": password,
        })
        assert login.status_code == 200
        assert login.json()["role"] == "admin"
