"""N2F3.7 on PostgreSQL: administrator decisions reuse the locked terminal path and outbox."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.orders.errors import ApiError
from tests.integration.test_fulfilment import accepted
from tests.integration.test_lifecycle import snapshot
from tests.integration.test_lifecycle import lifecycle_db as _lifecycle_database  # noqa: F401

pytestmark = pytest.mark.integration
REASON = "Requester showed the errand never arrived."


async def delivered(lifecycle_db):
    database, repo, order_id, owner, courier = await accepted(lifecycle_db)
    await repo.transition(order_id, courier, "pickup")
    await repo.transition(order_id, courier, "deliver")
    return database, repo, order_id, owner, courier


async def test_admin_fails_a_delivered_errand_once_and_releases_credits(lifecycle_db):
    database, repo, order_id, _, _ = await delivered(lifecycle_db)
    admin, dispute = uuid4(), uuid4()
    await repo.decide(order_id, admin, "fail", dispute_id=dispute, reason=REASON)
    before = await snapshot(database, order_id)
    await asyncio.gather(
        *[repo.decide(order_id, admin, "fail", dispute_id=dispute, reason=REASON) for _ in range(20)]
    )
    assert await snapshot(database, order_id) == before
    row, history, events = before
    assert row["state"] == "FAILED" and row["delivered_at"] is not None
    assert (row["failed_by"], row["decided_by"], row["decision_dispute_id"]) == (
        admin,
        admin,
        dispute,
    )
    assert (row["failure_reason"], row["failure_details"]) == ("ADMIN_DECISION", REASON)
    assert (history[-1]["actor_type"], history[-1]["dispute_id"]) == ("ADMIN", dispute)
    assert history[-1]["previous_state"] == "DELIVERED"
    # The release event carries no payout, exactly like a participant failure.
    assert len(events) == 1 and events[0]["event_type"] == "order.failed.v1"
    assert events[0]["amount"] is None


async def test_admin_completes_a_delivered_errand_and_pays_the_courier(lifecycle_db):
    database, repo, order_id, owner, courier = await delivered(lifecycle_db)
    dispute = uuid4()
    await repo.decide(order_id, uuid4(), "complete", dispute_id=dispute)
    row, history, events = await snapshot(database, order_id)
    assert row["state"] == "COMPLETED" and row["decision_dispute_id"] == dispute
    assert history[-1]["actor_type"] == "ADMIN"
    assert [event["event_type"] for event in events] == ["order.completed.v1"]
    assert (events[0]["requester_id"], events[0]["courier_id"]) == (owner, courier)
    assert events[0]["amount"] == row["reward"]


async def outcome(coroutine):
    try:
        return await coroutine
    except ApiError as error:
        return error


async def test_requester_confirmation_racing_an_admin_failure_settles_once(lifecycle_db):
    database, repo, order_id, owner, _ = await delivered(lifecycle_db)
    results = await asyncio.gather(
        outcome(repo.transition(order_id, owner, "complete")),
        outcome(repo.decide(order_id, uuid4(), "fail", dispute_id=uuid4(), reason=REASON)),
    )
    assert sum(isinstance(result, ApiError) for result in results) == 1
    row, _, events = await snapshot(database, order_id)
    assert row["state"] in ("COMPLETED", "FAILED") and len(events) == 1


async def test_completed_errands_are_never_reversed(lifecycle_db):
    database, repo, order_id, owner, _ = await delivered(lifecycle_db)
    await repo.transition(order_id, owner, "complete")
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        await repo.decide(order_id, uuid4(), "fail", dispute_id=uuid4(), reason=REASON)
    row, _, events = await snapshot(database, order_id)
    assert row["state"] == "COMPLETED" and len(events) == 1


async def test_database_rejects_a_delivered_failure_without_an_admin_decision(lifecycle_db):
    database, repo, order_id, owner, _ = await delivered(lifecycle_db)
    with pytest.raises(SQLAlchemyError):
        async with database.session_context() as session, session.begin():
            await session.execute(
                text(
                    "UPDATE order_service.orders SET state = 'FAILED', failed_at = now(), "
                    "failed_by = :owner, failure_reason = 'ITEM_DAMAGED' WHERE id = :id"
                ),
                {"owner": owner, "id": order_id},
            )
