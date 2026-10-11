"""LOCAL TEST DOUBLE ONLY. Not a Credit Service, wallet or production dependency."""

import asyncio
import hmac
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager, suppress
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import aio_pika
from fastapi import Depends, FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt

log = logging.getLogger("credit-simulator")


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operationId: UUID
    requesterId: UUID
    amount: StrictInt = Field(gt=0, le=2_147_483_647)


class TerminalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eventId: UUID
    eventType: Literal["order.cancelled.v1", "order.expired.v1"]
    orderId: UUID
    reservationId: UUID
    occurredAt: AwareDatetime


class StubError(Exception):
    def __init__(self, status: int, code: str):
        self.status, self.code = status, code


class Store:
    def __init__(self, path: str):
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reservations (
                    order_id TEXT PRIMARY KEY, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def read(db, order_id):
        row = db.execute(
            "SELECT body FROM reservations WHERE order_id = ?", (str(order_id),)
        ).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def save(db, value):
        db.execute("INSERT OR REPLACE INTO reservations VALUES (?, ?)",
                   (value["orderId"], json.dumps(value)))

    def get(self, order_id):
        with self.connect() as db:
            return self.read(db, order_id)

    def change(self, order_id, request: Request, abort=False, mode="success"):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = self.read(db, order_id)
            identity = request.model_dump(mode="json")
            if previous and any(previous[key] != value for key, value in identity.items()):
                raise StubError(409, "IDENTITY_CONFLICT")
            if previous:
                if abort and previous["state"] != "CLOSED":
                    previous["state"] = "CLOSED"
                    self.save(db, previous)
                return previous
            if not abort and mode != "success":
                raise StubError(409, mode.upper())
            value = {**identity, "orderId": str(order_id),
                     "reservationId": None if abort else str(uuid4()),
                     "state": "CLOSED" if abort else "RESERVED"}
            self.save(db, value)
            return value

    def release(self, event: TerminalEvent):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM events WHERE event_id = ?",
                          (str(event.eventId),)).fetchone():
                return
            value = self.read(db, event.orderId)
            if not value or value["reservationId"] != str(event.reservationId):
                raise ValueError("Unknown reservation")
            if value["state"] == "RESERVED":
                value["state"] = "RELEASED"
                self.save(db, value)
            db.execute("INSERT INTO events VALUES (?)", (str(event.eventId),))


async def consume(store, broker_url, ready):
    while True:
        try:
            async with await aio_pika.connect(broker_url) as connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                exchange = await channel.declare_exchange(
                    "foc.order-demo.events", aio_pika.ExchangeType.TOPIC, durable=True
                )
                queue = await channel.declare_queue("credit-simulator.releases", durable=True)
                for key in ("order.cancelled.v1", "order.expired.v1"):
                    await queue.bind(exchange, routing_key=key)
                ready.set()
                async with queue.iterator() as messages:
                    async for message in messages:
                        try:
                            event = TerminalEvent.model_validate_json(message.body)
                            if message.routing_key != event.eventType:
                                raise ValueError("Routing mismatch")
                            store.release(event)
                        except ValueError:
                            log.warning("SIMULATION: rejected invalid/unmatched terminal event")
                            await message.reject(requeue=False)
                        except sqlite3.Error:
                            await message.nack(requeue=True)
                            await asyncio.sleep(1)
                        else:
                            await message.ack()
                            log.info("SIMULATION: release recorded for order %s", event.orderId)
        except (OSError, aio_pika.exceptions.AMQPException):
            log.warning("SIMULATION: broker unavailable; reconnecting")
        finally:
            ready.clear()
        await asyncio.sleep(2)


def create_app(store: Store, secret: str, mode="success", broker_url=None):
    modes = {"success", "insufficient_credit", "wallet_not_ready", "unavailable"}
    if not secret or mode not in modes:
        raise ValueError("Simulator requires a secret and a supported mode")
    ready = asyncio.Event()

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(consume(store, broker_url, ready)) if broker_url else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="LOCAL Credit simulator — NOT real Credit", lifespan=lifespan)

    @app.exception_handler(StubError)
    async def error_handler(request, error):
        return JSONResponse(status_code=error.status, content={
            "error": {"code": error.code, "message": "Local Credit simulation response."}
        })

    def authorize(x_foc_service_secret: str = Header(default="")):
        if not hmac.compare_digest(x_foc_service_secret.encode(), secret.encode()):
            raise StubError(401, "UNAUTHENTICATED")
        if mode == "unavailable":
            raise StubError(503, "CREDIT_UNAVAILABLE")

    @app.get("/health/ready")
    def health():
        if broker_url and not ready.is_set():
            raise StubError(503, "BROKER_UNAVAILABLE")
        return {"simulation": True, "mode": mode}

    prefix = "/v1/internal/order-reservations/{order_id}"

    @app.get(prefix, dependencies=[Depends(authorize)])
    def status(order_id: UUID):
        value = store.get(order_id)
        if not value:
            raise StubError(404, "NOT_FOUND")
        return value

    @app.put(prefix, dependencies=[Depends(authorize)])
    def reserve(order_id: UUID, request: Request):
        return store.change(order_id, request, mode=mode)

    @app.put(prefix + "/creation-abort", dependencies=[Depends(authorize)])
    def abort(order_id: UUID, request: Request):
        return store.change(order_id, request, abort=True)

    return app


def from_environment():
    if os.environ.get("CREDIT_SIMULATOR_ENABLED") != "local-only":
        raise RuntimeError("Explicit local-only opt-in required")
    return create_app(Store(os.environ.get("SIMULATOR_DB", "/data/credit.sqlite")),
                      os.environ["CREDIT_SERVICE_SECRET"],
                      os.environ.get("SIMULATOR_MODE", "success"), os.environ["RABBITMQ_URL"])


if __name__ == "__main__":
    # Local Docker exec inspection only: no public status/admin endpoint or credentials printed.
    db_path = os.environ.get("SIMULATOR_DB", "/data/credit.sqlite")
    if not Path(db_path).is_file():
        raise SystemExit("No simulator data exists yet")
    with sqlite3.connect(db_path) as db:
        for (body,) in db.execute("SELECT body FROM reservations"):
            value = json.loads(body)
            print(json.dumps({key: value[key] for key in ("orderId", "amount", "state")}))
        count = db.execute("SELECT count(*) FROM events").fetchone()[0]
        print("Simulated releases consumed:", count)
