import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.main import create_app
from app.orders.errors import ApiError
from app.orders.lifecycle_repository import LifecycleRepository
from tests.integration.test_fulfilment import accepted, make_due
from tests.integration.test_lifecycle import TokenIdentity, snapshot
from tests.integration.test_lifecycle import lifecycle_db as _lifecycle_database  # noqa: F401

pytestmark = pytest.mark.integration
REPORT = {"reason": "ITEM_DAMAGED", "details": "Item damaged after pickup"}


@pytest.mark.parametrize("picked_up", [False, True])
@pytest.mark.parametrize("actor_role", ["requester", "courier"])
async def test_failure_http_metadata_history_and_100_retries(lifecycle_db, picked_up, actor_role):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    if picked_up:
        await repo.transition(order_id, courier, "pickup")
    actor = owner if actor_role == "requester" else courier
    app = create_app(
        Settings(_env_file=None),
        database=database,
        clients=TokenIdentity(),
        lifecycle_repository=repo,
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as http:
            path, headers = f"/v1/orders/{order_id}/fail", {"Authorization": f"Bearer {actor}"}
            result = await http.post(path, headers=headers, json=REPORT)
            assert result.status_code == 200
            assert result.json()["state"] == "FAILED" and result.json()["failedBy"] == str(actor)
            before = await snapshot(database, order_id)
            replies = await asyncio.gather(
                *[http.post(path, headers=headers, json=REPORT) for _ in range(100)]
            )
            assert all(reply.status_code == 200 for reply in replies)
            assert await snapshot(database, order_id) == before
            row, history, events = before
            assert len(history) == (4 if picked_up else 3) and len(events) == 1
            assert history[-1]["failure_reason"] == row["failure_reason"] == REPORT["reason"]
            assert history[-1]["actor_id"] == actor and events[0]["event_type"] == "order.failed.v1"
            assert events[0]["amount"] is events[0]["courier_id"] is None
            history_response = await http.get(
                path.removesuffix("/fail") + "/history", headers=headers
            )
            assert history_response.json()["items"][-1]["failureDetails"] == REPORT["details"]
            assert (
                await http.post(path, headers={"Authorization": f"Bearer {uuid4()}"}, json=REPORT)
            ).status_code == 404


async def attempt(repo, order_id, actor, action, failure=None):
    try:
        return await repo.transition(order_id, actor, action, failure=failure)
    except ApiError as error:
        return error


async def test_competing_participants_record_one_failure_and_release(lifecycle_db):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    results = await asyncio.gather(
        *[
            attempt(repo, order_id, actor, "fail", {"reason": "ITEM_UNAVAILABLE"})
            for actor in (owner, courier)
        ]
    )
    assert sum(isinstance(result, ApiError) for result in results) == 1
    row, history, events = await snapshot(database, order_id)
    assert row["state"] == "FAILED" and len(history) == 3 and len(events) == 1
    assert history[-1]["actor_id"] == row["failed_by"]


async def test_100_simultaneous_first_failure_requests_emit_one_release(lifecycle_db):
    database, repo, order_id, owner, _ = await accepted(lifecycle_db)
    await asyncio.gather(
        *[repo.transition(order_id, owner, "fail", failure=REPORT) for _ in range(100)]
    )
    _, history, events = await snapshot(database, order_id)
    assert len(history) == 3 and len(events) == 1


@pytest.mark.parametrize("complete", [False, True])
async def test_delivery_or_completion_cannot_be_reversed_by_failure(lifecycle_db, complete):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    await repo.transition(order_id, courier, "pickup")
    await repo.transition(order_id, courier, "deliver")
    if complete:
        await repo.transition(order_id, owner, "complete")
    before = await snapshot(database, order_id)
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        await repo.transition(order_id, owner, "fail", failure=REPORT)
    assert await snapshot(database, order_id) == before


async def test_delivery_failure_race_has_one_valid_outcome(lifecycle_db):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    await repo.transition(order_id, courier, "pickup")
    results = await asyncio.gather(
        attempt(repo, order_id, courier, "deliver"), attempt(repo, order_id, owner, "fail", REPORT)
    )
    assert sum(isinstance(result, ApiError) for result in results) == 1
    row, history, events = await snapshot(database, order_id)
    assert len(history) == 4 and row["state"] in ("FAILED", "DELIVERED")
    assert len(events) == (1 if row["state"] == "FAILED" else 0)


async def test_pickup_failure_race_always_ends_failed_with_valid_history(lifecycle_db):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    results = await asyncio.gather(
        attempt(repo, order_id, courier, "pickup"), attempt(repo, order_id, owner, "fail", REPORT)
    )
    row, history, events = await snapshot(database, order_id)
    assert row["state"] == "FAILED" and len(events) == 1
    assert history[-1]["new_state"] == "FAILED" and len(history) in (3, 4)
    if isinstance(results[0], ApiError):
        assert len(history) == 3 and row["picked_up_at"] is None
    else:
        assert len(history) == 4 and row["failed_at"] >= row["picked_up_at"]


async def test_failure_event_error_rolls_back_every_record(lifecycle_db):
    database, _, order_id, owner, _ = await accepted(lifecycle_db)

    class BrokenRepository(LifecycleRepository):
        async def _record(self, session, row, values, actor, now):
            return await super()._record(
                session, {**row, "reservation_id": None}, values, actor, now
            )

    before = await snapshot(database, order_id)
    with pytest.raises(SQLAlchemyError):
        await BrokenRepository(database.session_context).transition(
            order_id, owner, "fail", failure=REPORT
        )
    assert await snapshot(database, order_id) == before


@pytest.mark.parametrize("late", [False, True])
async def test_failure_overdue_worker_preserves_history_without_marking_early_failure(
    lifecycle_db, late
):
    database, repo, order_id, owner, _ = await accepted(lifecycle_db)
    if late:
        await make_due(database, order_id)
    failed = await repo.transition(order_id, owner, "fail", failure=REPORT)
    before = await snapshot(database, order_id)
    await repo.overdue_batch(100)
    assert await snapshot(database, order_id) == before
    assert failed["overdue_at"] == (failed["delivery_deadline"] if late else None)


async def test_app_role_can_fail_but_cannot_rewrite_failure_history(lifecycle_db):
    database, _, order_id, _, courier = await accepted(lifecycle_db)

    @asynccontextmanager
    async def restricted():
        async with database.session_context() as session:
            await session.execute(text("SET ROLE order_service_app"))
            await session.commit()
            try:
                yield session
            finally:
                await session.rollback()
                await session.execute(text("RESET ROLE"))
                await session.commit()

    await LifecycleRepository(restricted).transition(order_id, courier, "fail", failure=REPORT)
    async with restricted() as session:
        assert not await session.scalar(
            text(
                "SELECT has_column_privilege(current_user, 'order_service.order_history', "
                "'failure_reason', 'UPDATE')"
            )
        )
    assert (await snapshot(database, order_id))[0]["failed_by"] == courier
