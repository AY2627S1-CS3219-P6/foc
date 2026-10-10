import asyncio
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import aio_pika
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from websockets.asyncio.client import connect

from app.config import Settings
from app.events import Envelope
from app.live import Connection, Hub
from app.outbox import Publisher
from tests.test_messages import send


@pytest.fixture
def broker_url():
    value = os.getenv("CHAT_TEST_RABBITMQ_URL")
    if not value:
        pytest.skip("CHAT_TEST_RABBITMQ_URL is not configured")
    from urllib.parse import urlsplit

    parsed = urlsplit(value)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 17425:
        pytest.fail("Broker tests require the isolated local port 17425")
    return value


async def receive(ws, kind, timeout=10):
    async with asyncio.timeout(timeout):
        while True:
            item = json.loads(await ws.recv())
            if item["type"] == kind:
                return item


@pytest_asyncio.fixture
async def processes(database, broker_url):
    root = Path(__file__).resolve().parents[1]
    env = {
        **os.environ,
        "DATABASE_URL": os.environ["CHAT_TEST_DATABASE_URL"],
        "RABBITMQ_URL": broker_url,
        "CHAT_SERVICE_SHARED_SECRET": "test-chat-secret",
        "USER_SERVICE_BASE_URL": "http://127.0.0.1:17430",
        "WEBSOCKET_SESSION_CHECK_SECONDS": "0.2",
        "OUTBOX_POLL_SECONDS": "0.1",
    }
    children = []
    try:
        for module, port in (
            ("tests.runtime:identity_app", 17430),
            ("app.main:app", 17431),
            ("app.main:app", 17432),
        ):
            children.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        module,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--no-access-log",
                        "--log-level",
                        "critical",
                        "--ws-max-size",
                        "65536",
                    ],
                    cwd=root,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            )
        async with httpx.AsyncClient(timeout=1) as client:
            async with asyncio.timeout(30):
                while True:
                    try:
                        for port in (17431, 17432):
                            r = await client.get(f"http://127.0.0.1:{port}/health/ready")
                            assert r.status_code == 200 and r.json()["delivery"] == "ready"
                        break
                    except (httpx.HTTPError, AssertionError):
                        await asyncio.sleep(0.2)
        children.append(
            subprocess.Popen(
                [sys.executable, "-m", "app.outbox"],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        )
        yield env
    finally:
        for child in children:
            child.terminate()
        for child in children:
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(timeout=5)
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)


@pytest.mark.integration
@pytest.mark.broker
async def test_cross_process_delivery_retries_and_revocation(processes, database, broker_url):
    async with httpx.AsyncClient() as client:
        a = (await client.post("http://127.0.0.1:17430/test/users")).json()
        b = (await client.post("http://127.0.0.1:17430/test/users")).json()
        c = (await client.post("http://127.0.0.1:17430/test/users")).json()
        headers = {"Authorization": f"Bearer {a['accessToken']}"}
        r = await client.post(
            "http://127.0.0.1:17431/v1/chat/conversations",
            headers=headers,
            json={"recipientUserId": b["userId"]},
        )
        assert r.status_code == 200, r.text
        cid = r.json()["conversationId"]
        async with (
            connect("ws://127.0.0.1:17431/v1/chat/ws", origin="http://localhost:3000") as wa,
            connect("ws://127.0.0.1:17432/v1/chat/ws", origin="http://localhost:3000") as wb,
            connect("ws://127.0.0.1:17432/v1/chat/ws", origin="http://localhost:3000") as wc,
        ):
            for ws, user in ((wa, a), (wb, b), (wc, c)):
                await ws.send(
                    json.dumps({"type": "authenticate", "accessToken": user["accessToken"]})
                )
                assert (await receive(ws, "ready"))["userId"] == user["userId"]
            command = send(UUID(cid), "persistent across processes").model_dump(mode="json")
            await wa.send(json.dumps(command))
            accepted = (await receive(wa, "message.accepted"))["message"]
            received = (await receive(wb, "message.created"))["message"]
            assert accepted == received
            await wa.send(json.dumps(command))
            assert (await receive(wa, "message.accepted"))["message"] == accepted
            await wc.send(json.dumps({**command, "clientMessageId": str(uuid4())}))
            assert (await receive(wc, "error"))["error"]["code"] == "CONVERSATION_NOT_FOUND"
            # Duplicate broker event must not produce a second rendered-message event.
            connection = await aio_pika.connect(broker_url)
            try:
                channel = await connection.channel()
                exchange = await channel.get_exchange("foc.chat.events")
                event = {
                    "eventId": str(uuid4()),
                    "eventType": "chat.message.created.v1",
                    "data": {
                        "conversationId": cid,
                        "messageId": accepted["messageId"],
                        "sequence": 1,
                    },
                }
                for _ in range(2):
                    await exchange.publish(
                        aio_pika.Message(json.dumps(event).encode()),
                        routing_key="chat.message.created.v1",
                        mandatory=False,
                    )
                with pytest.raises(TimeoutError):
                    await receive(wb, "message.created", timeout=0.4)
            finally:
                await connection.close()
            await client.post(
                "http://127.0.0.1:17430/test/revoke", json={"token": b["accessToken"]}
            )
            from websockets.exceptions import ConnectionClosed

            with pytest.raises(ConnectionClosed):
                async with asyncio.timeout(3):
                    while True:
                        await wb.recv()


@pytest.mark.integration
@pytest.mark.broker
async def test_publisher_confirm_lease_and_minimal_payload(
    database, identity, directory, broker_url
):
    from app.service import ChatService

    a, b = directory.user(), directory.user()
    chat = ChatService(database, identity)
    cid = UUID((await chat.create(a, b))["conversationId"])
    stored = await chat.send(a, send(cid, "never publish this body"))
    publisher = Publisher(Settings(_env_file=None, rabbitmq_url=broker_url), database)
    # Drain preceding test events; these resources belong exclusively to Chat Service.
    try:
        while await publisher.run_once():
            pass
        async with database.transaction() as session:
            row = (
                (
                    await session.execute(
                        text(
                            "SELECT * FROM chat_service.outbox_events "
                            "WHERE payload->>'messageId'=:mid"
                        ),
                        {"mid": stored["messageId"]},
                    )
                )
                .mappings()
                .one()
            )
            assert row["published_at"] is not None and row["lease_token"] is None
            assert set(row["payload"]) == {"conversationId", "messageId", "sequence"}
        # Two workers cannot claim the same leased event.
        await chat.send(a, send(cid))
        p2 = Publisher(Settings(_env_file=None, rabbitmq_url=broker_url), database)
        claims = await asyncio.gather(publisher.claim(), p2.claim())
        claimed = [r for r in claims if r]
        assert len({r["id"] for r in claimed}) == len(claimed)
        for row in claimed:
            await publisher.publish(row)
            await publisher.finish(row, True)
        await p2.close()
    finally:
        await publisher.close()


def test_outgoing_buffer_is_bounded():
    from app.identity import Principal

    connection = Connection(None, Principal(uuid4(), 9999999999, "token"), asyncio.Queue(1))
    connection.offer({"type": "ready"})
    connection.offer({"type": "ready"})
    assert connection.stopped.is_set() and connection.close_code == 1013


@pytest.mark.integration
async def test_live_block_status_and_authoritative_event(chat, directory):
    a, b, c = directory.user(), directory.user(), directory.user()
    cid = UUID((await chat.create(a, b))["conversationId"])
    stored = await chat.send(a, send(cid))
    envelope = Envelope(
        eventId=uuid4(),
        eventType="chat.message.created.v1",
        data={"conversationId": str(cid), "messageId": stored["messageId"], "sequence": 1},
    )
    hub = Hub(chat, Settings(_env_file=None))
    from app.events import MessageEvent

    event = MessageEvent.model_validate(envelope.data)
    assert await chat.live_message(c, event) is None
    assert await chat.live_message(b, event) == stored
    await chat.set_block(b, a, True)
    assert await chat.live_message(b, event) is None
    await chat.set_block(b, a, False)
    directory.people[a]["accountStatus"] = "DELETED"
    assert await chat.live_message(b, event) is None
    hub.sync()  # empty hub is safe on subscription churn
