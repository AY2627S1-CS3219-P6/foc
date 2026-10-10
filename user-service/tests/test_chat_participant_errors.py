from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize(
    "failure",
    [None, OSError("private-db-url"), OperationalError("private-query", {}, Exception("secret"))],
)
async def test_participant_database_failure_never_fabricates_missing_ids(failure) -> None:
    app = create_app(settings=Settings(_env_file=None, chat_service_shared_secret="chat-only"))
    if failure is not None:

        async def broken_session():
            raise failure
            yield

        app.state.database.session = broken_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/internal/chat/participants",
            headers={
                "X-FoC-Service-Secret": "chat-only",
                "X-Correlation-ID": "lookup-trace",
            },
            json={"userIds": [str(uuid4())]},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_NOT_READY"
    assert response.json()["error"]["correlationId"] == "lookup-trace"
    assert response.headers["Cache-Control"] == "no-store"
    for value in ("private-db-url", "private-query", "chat-only", "missingUserIds"):
        assert value not in response.text
