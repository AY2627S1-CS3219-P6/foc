"""Opt-in real RabbitMQ checks, not a production Credit consumer."""

import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import aio_pika
import pytest
from sqlalchemy import update

from app.core.config import Settings
from app.orders.outbox import OutboxRepository, RabbitPublisher, event_payload, publish_once
from app.orders.tables import outbox
from tests.integration.test_lifecycle import lifecycle_db as _lifecycle_database  # noqa: F401
from tests.integration.test_lifecycle import snapshot

pytestmark = pytest.mark.integration


@pytest.fixture
async def broker():
    url = os.environ.get("ORDER_TEST_RABBITMQ_URL")
    if not url:
        pytest.skip("Set ORDER_TEST_RABBITMQ_URL to a disposable broker")
    connection = await aio_pika.connect(url)
    channel = await connection.channel(publisher_confirms=True, on_return_raises=True)
    name = f"order-check-{uuid4().hex}"
    exchange = await channel.declare_exchange(name, aio_pika.ExchangeType.TOPIC, durable=True)
    settings = Settings(_env_file=None, rabbitmq_url=url, outbox_exchange_name=name)
    publisher = RabbitPublisher(settings)
    queue = await channel.declare_queue(name + "-credit-test-double", durable=True)
    try:
        yield channel, exchange, queue, publisher
    finally:
        await publisher.close()
        await queue.delete(if_unused=False, if_empty=False)
        await exchange.delete(if_unused=False)
        await connection.close()


async def due_first(database, order_id):
    async with database.session_context() as session, session.begin():
        await session.execute(
            update(outbox)
            .where(outbox.c.order_id == order_id)
            .values(next_attempt_at=datetime(1970, 1, 1, tzinfo=UTC))
        )


async def test_unroutable_event_retries_then_reaches_durable_queue(lifecycle_db, broker):
    database, repo, seed = lifecycle_db
    _, exchange, queue, publisher = broker
    order_id, owner = await seed()
    await repo.transition(order_id, owner, "cancel")
    await due_first(database, order_id)
    out = OutboxRepository(database.session_context)
    for _ in range(4):
        await due_first(database, order_id)
        assert await publish_once(out, publisher)
    _, _, events = await snapshot(database, order_id)
    assert events[0]["state"] == "PENDING"
    assert events[0]["last_error_code"] == "PUBLISH_UNAVAILABLE"
    event_id = events[0]["event_id"]
    await queue.bind(exchange, routing_key="order.cancelled.v1")
    await due_first(database, order_id)
    assert await publish_once(out, publisher)
    _, _, events = await snapshot(database, order_id)
    assert events[0]["state"] == "PUBLISHED" and events[0]["publish_attempts"] == 5
    message = await queue.get(timeout=3)
    assert message.message_id == str(event_id)
    assert json.loads(message.body) == event_payload(events[0])
    assert message.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
    await message.ack()


async def test_crash_after_broker_confirmation_replays_same_event(lifecycle_db, broker):
    database, repo, seed = lifecycle_db
    _, exchange, queue, publisher = broker
    await queue.bind(exchange, routing_key="order.expired.v1")
    order_id, _ = await seed(expired=True)
    await repo.expire_batch(100)
    await due_first(database, order_id)
    out = OutboxRepository(database.session_context)
    original = await out.claim(30)
    await publisher.publish(original)
    # Simulate a process death after the broker ack, before the DB acknowledgment.
    async with database.session_context() as session, session.begin():
        await session.execute(
            update(outbox)
            .where(outbox.c.event_id == original["event_id"])
            .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert await publish_once(OutboxRepository(database.session_context), publisher)
    first, second = await queue.get(timeout=3), await queue.get(timeout=3)
    assert first.message_id == second.message_id == str(original["event_id"])
    assert first.body == second.body
    await first.ack()
    await second.ack()
    assert (await snapshot(database, order_id))[2][0]["state"] == "PUBLISHED"


async def test_broken_connection_preserves_event_and_next_attempt_reconnects(lifecycle_db, broker):
    database, repo, seed = lifecycle_db
    _, exchange, queue, publisher = broker
    await queue.bind(exchange, routing_key="order.cancelled.v1")
    order_id, owner = await seed()
    await repo.transition(order_id, owner, "cancel")
    item = (await snapshot(database, order_id))[2][0]
    await publisher.publish(item)  # Establish a real connection.
    await (await queue.get(timeout=3)).ack()
    await publisher.connection.close()
    await due_first(database, order_id)
    out = OutboxRepository(database.session_context)
    assert await publish_once(out, publisher)
    assert (await snapshot(database, order_id))[2][0]["state"] == "PENDING"
    await due_first(database, order_id)
    assert await publish_once(out, publisher)
    assert (await snapshot(database, order_id))[2][0]["state"] == "PUBLISHED"
    message = await queue.get(timeout=3)
    assert message.message_id == str(item["event_id"])
    await message.ack()
