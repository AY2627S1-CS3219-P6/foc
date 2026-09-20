from __future__ import annotations

from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


class StubDatabase:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def ping(self) -> bool:
        return self.ready

    async def dispose(self) -> None:
        return None


def build_test_app(database_ready: bool):
    return create_app(
        settings=Settings(_env_file=None, environment="test"),
        database=StubDatabase(database_ready),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_live_reports_service_status_and_echoes_safe_correlation_id() -> None:
    app = build_test_app(database_ready=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Correlation-ID": "request-42"})

    assert response.status_code == 200
    assert response.json() == {"status": "live"}
    assert response.headers["X-Correlation-ID"] == "request-42"


@pytest.mark.asyncio
async def test_live_replaces_malformed_correlation_id() -> None:
    app = build_test_app(database_ready=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Correlation-ID": "bad value"})

    assert response.status_code == 200
    assert UUID(hex=response.headers["X-Correlation-ID"])


@pytest.mark.asyncio
async def test_ready_returns_ok_when_postgresql_probe_succeeds() -> None:
    app = build_test_app(database_ready=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_returns_safe_error_when_postgresql_probe_fails() -> None:
    app = build_test_app(database_ready=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready", headers={"X-Correlation-ID": "readiness-1"})

    assert response.status_code == 503
    assert response.headers["X-Correlation-ID"] == "readiness-1"
    assert response.json() == {
        "error": {
            "code": "SERVICE_NOT_READY",
            "message": "A required service dependency is not ready.",
            "correlationId": "readiness-1",
            "fieldErrors": [],
        }
    }
