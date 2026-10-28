"""N2F3.2-N2F3.6 dispute API; N2NFR3.3-N2NFR3.5 retries, conflicts and rejected attempts."""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.admin.disputes import (
    DisputeNotFound,
    IdempotencyKeyReused,
    InvalidTransition,
    ReasonRequired,
    VersionConflict,
)
from app.admin.errors import unavailable
from app.core.config import Settings
from app.main import create_app
from tests.admin_fakes import FakeDisputes, FakeIdentity, FakeOrders, NoDatabase, dispute_row

AUTH = {"Authorization": "Bearer admin-token"}
KEY = str(uuid4())


def client_for(disputes=None, orders=None, identity=None):
    app = create_app(
        Settings(_env_file=None),
        NoDatabase(),
        identity=identity or FakeIdentity(),
        disputes=disputes or FakeDisputes(),
        orders=orders or FakeOrders(),
    )
    return AsyncClient(transport=ASGITransport(app), base_url="http://test")


def body(**overrides):
    return {
        "orderId": str(uuid4()),
        "description": "  Courier marked it delivered; nothing arrived.  ",
        "evidenceRefs": ["chat:42"],
        **overrides,
    }


async def create(client, payload=None, **headers):
    return await client.post(
        "/v1/admin/disputes",
        json=payload or body(),
        headers={**AUTH, "Idempotency-Key": KEY, **headers},
    )


async def test_ordinary_users_cannot_use_dispute_routes():
    disputes, orders = FakeDisputes(), FakeOrders()
    dispute_id = uuid4()
    async with client_for(disputes, orders, FakeIdentity("USER")) as client:
        statuses = [
            (await create(client)).status_code,
            (await client.get("/v1/admin/disputes", headers=AUTH)).status_code,
            (await client.get(f"/v1/admin/disputes/{dispute_id}", headers=AUTH)).status_code,
            (
                await client.post(
                    f"/v1/admin/disputes/{dispute_id}/transitions",
                    json={"toStatus": "UNDER_REVIEW", "expectedVersion": 1},
                    headers=AUTH,
                )
            ).status_code,
            (await client.get("/v1/admin/audit-log", headers=AUTH)).status_code,
        ]
    assert statuses == [403] * 5
    assert disputes.calls == [] and orders.calls == []


async def test_recording_a_dispute_confirms_the_errand_and_starts_open():
    disputes, orders, identity = FakeDisputes(), FakeOrders(), FakeIdentity()
    payload = body()
    async with client_for(disputes, orders, identity) as client:
        response = await create(client, payload, **{"X-Correlation-ID": "req-1"})
    assert response.status_code == 201
    created = response.json()
    assert (created["status"], created["version"]) == ("OPEN", 1)
    assert created["description"] == "Courier marked it delivered; nothing arrived."
    assert created["evidenceRefs"] == ["chat:42"]
    assert [entry["toStatus"] for entry in created["history"]] == ["OPEN"]
    assert orders.calls == [(UUID(payload["orderId"]), "admin-token")]
    values = disputes.calls[0][1]
    assert values["actor"] == identity.user_id and str(values["key"]) == KEY
    assert values["correlation_id"] == "req-1"


async def test_replaying_the_same_request_returns_the_original_dispute():
    disputes = FakeDisputes()
    disputes.created = False
    async with client_for(disputes) as client:
        response = await create(client)
    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"


@pytest.mark.parametrize("key", [None, "", "not-a-uuid"])
async def test_recording_needs_an_idempotency_key(key):
    disputes, orders = FakeDisputes(), FakeOrders()
    headers = dict(AUTH) if key is None else {**AUTH, "Idempotency-Key": key}
    async with client_for(disputes, orders) as client:
        response = await client.post("/v1/admin/disputes", json=body(), headers=headers)
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert disputes.calls == [] and orders.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        body(description="   "),
        body(evidenceRefs=[f"ref-{index}" for index in range(11)]),
        body(evidenceRefs=["   "]),
        body(status="RESOLVED"),
        {"description": "No errand reference"},
    ],
)
async def test_invalid_dispute_bodies_are_rejected(payload):
    disputes = FakeDisputes()
    async with client_for(disputes) as client:
        response = await create(client, payload)
    assert response.status_code == 422
    assert disputes.calls == []


async def test_unknown_errand_is_rejected_and_the_attempt_audited():
    disputes = FakeDisputes()
    payload = body()
    async with client_for(disputes, FakeOrders(known=False)) as client:
        response = await create(client, payload)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "ORDER_NOT_FOUND")
    assert disputes.calls == []
    rejection = disputes.rejections[0]
    assert (rejection["action"], rejection["target_type"], rejection["error_code"]) == (
        "DISPUTE_CREATE",
        "ORDER",
        "ORDER_NOT_FOUND",
    )
    assert rejection["target_id"] == UUID(payload["orderId"])


async def test_order_outage_stores_nothing_but_the_rejection():
    disputes = FakeDisputes()
    async with client_for(disputes, FakeOrders(error=unavailable("ORDER_UNAVAILABLE"))) as client:
        response = await create(client)
    assert response.status_code == 503
    assert disputes.calls == []
    assert disputes.rejections[0]["error_code"] == "ORDER_UNAVAILABLE"


async def test_reused_key_with_a_different_body_conflicts():
    disputes = FakeDisputes()
    disputes.error = IdempotencyKeyReused()
    async with client_for(disputes) as client:
        response = await create(client)
    assert (response.status_code, response.json()["error"]["code"]) == (
        409,
        "IDEMPOTENCY_KEY_REUSED",
    )
    assert len(disputes.rejections) == 1


async def test_status_change_returns_the_updated_dispute():
    disputes = FakeDisputes()
    disputes.row = dispute_row()
    dispute_id = disputes.row["id"]
    async with client_for(disputes) as client:
        response = await client.post(
            f"/v1/admin/disputes/{dispute_id}/transitions",
            json={"toStatus": "UNDER_REVIEW", "reason": "   ", "expectedVersion": 1},
            headers=AUTH,
        )
    assert response.status_code == 200
    assert (response.json()["status"], response.json()["version"]) == ("UNDER_REVIEW", 2)
    assert disputes.calls[0][2]["reason"] is None  # a blank reason is no reason


@pytest.mark.parametrize(
    "error,status,code",
    [
        (InvalidTransition(), 409, "INVALID_TRANSITION"),
        (VersionConflict(), 409, "VERSION_CONFLICT"),
        (ReasonRequired(), 422, "REASON_REQUIRED"),
        (DisputeNotFound(), 404, "DISPUTE_NOT_FOUND"),
    ],
)
async def test_rejected_status_changes_are_reported_and_audited(error, status, code):
    disputes = FakeDisputes()
    disputes.row = dispute_row()
    disputes.error = error
    dispute_id = disputes.row["id"]
    async with client_for(disputes) as client:
        response = await client.post(
            f"/v1/admin/disputes/{dispute_id}/transitions",
            json={"toStatus": "RESOLVED", "reason": "Refund agreed", "expectedVersion": 1},
            headers=AUTH,
        )
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    rejection = disputes.rejections[0]
    assert (rejection["action"], rejection["target_type"], rejection["target_id"]) == (
        "DISPUTE_TRANSITION",
        "DISPUTE",
        dispute_id,
    )
    assert rejection["error_code"] == code


async def test_audit_failure_does_not_hide_the_original_rejection():
    disputes = FakeDisputes()
    disputes.row = dispute_row()
    disputes.error = VersionConflict()
    disputes.audit_error = OperationalError("INSERT", {}, Exception("database down"))
    async with client_for(disputes) as client:
        response = await client.post(
            f"/v1/admin/disputes/{disputes.row['id']}/transitions",
            json={"toStatus": "UNDER_REVIEW", "expectedVersion": 1},
            headers=AUTH,
        )
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"


@pytest.mark.parametrize(
    "payload",
    [
        {"toStatus": "OPEN", "expectedVersion": 1},
        {"toStatus": "RESOLVED", "reason": "Refund agreed"},
        {"toStatus": "RESOLVED", "reason": "Refund agreed", "expectedVersion": 0},
        {"toStatus": "RESOLVED", "reason": "Refund agreed", "expectedVersion": "1"},
    ],
)
async def test_invalid_status_change_bodies_are_rejected(payload):
    disputes = FakeDisputes()
    async with client_for(disputes) as client:
        response = await client.post(
            f"/v1/admin/disputes/{uuid4()}/transitions", json=payload, headers=AUTH
        )
    assert response.status_code == 422
    assert disputes.calls == []


async def test_dispute_detail_listing_and_audit_log():
    disputes = FakeDisputes()
    row = dispute_row(evidence_refs=["chat:42"])
    disputes.row = row
    disputes.page = ([row], 1)
    disputes.audit = (
        [
            {
                "id": uuid4(),
                "actor_id": row["created_by"],
                "action": "DISPUTE_CREATE",
                "target_type": "DISPUTE",
                "target_id": row["id"],
                "outcome": "SUCCESS",
                "error_code": None,
                "correlation_id": "req-1",
                "occurred_at": row["created_at"],
            }
        ],
        1,
    )
    async with client_for(disputes) as client:
        detail = await client.get(f"/v1/admin/disputes/{row['id']}", headers=AUTH)
        missing = await client.get(f"/v1/admin/disputes/{uuid4()}", headers=AUTH)
        listing = await client.get(
            f"/v1/admin/disputes?status=OPEN&orderId={row['order_id']}&pageSize=10", headers=AUTH
        )
        audit = await client.get("/v1/admin/audit-log?outcome=SUCCESS", headers=AUTH)
    assert detail.json()["evidenceRefs"] == ["chat:42"]
    assert missing.status_code == 404
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["disputeId"] == str(row["id"])
    assert (
        "disputes_page",
        {"status": "OPEN", "order_id": row["order_id"], "page": 1, "page_size": 10},
    ) in disputes.calls
    assert audit.json()["items"][0]["outcome"] == "SUCCESS"


@pytest.mark.parametrize(
    "url",
    [
        "/v1/admin/disputes?status=CLOSED",
        "/v1/admin/disputes?pageSize=51",
        "/v1/admin/disputes?sort=asc",
        "/v1/admin/audit-log?outcome=MAYBE",
    ],
)
async def test_invalid_list_filters_are_rejected(url):
    async with client_for() as client:
        assert (await client.get(url, headers=AUTH)).status_code == 422
