import pytest
from httpx import AsyncClient, ASGITransport

from server import app


class HealthyDatabase:
    async def command(self, command_name):
        assert command_name == "ping"
        return {"ok": 1}


class UnavailableDatabase:
    async def command(self, command_name):
        raise RuntimeError("database unavailable")


@pytest.mark.asyncio
async def test_health_liveness_probe():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "foundations-api"


@pytest.mark.asyncio
async def test_ready_probe_requires_database_connectivity():
    original_db = app.state.db
    app.state.db = HealthyDatabase()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
    finally:
        app.state.db = original_db

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "foundations-api",
        "database": "ok",
    }


@pytest.mark.asyncio
async def test_ready_probe_returns_503_when_database_is_unavailable():
    original_db = app.state.db
    app.state.db = UnavailableDatabase()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
    finally:
        app.state.db = original_db

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "foundations-api",
        "database": "unavailable",
    }
