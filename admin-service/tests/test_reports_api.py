"""N2F3.2: errand participants report problems; only their own reports are visible to them."""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.admin.disputes import ReportAlreadyOpen
from app.core.config import Settings
from app.main import create_app
from tests.admin_fakes import FakeDisputes, FakeIdentity, FakeOrders, NoDatabase, dispute_row

AUTH = {"Authorization": "Bearer user-token"}
KEY = str(uuid4())


def client_for(disputes=None, orders=None, identity=None):
    app = create_app(
        Settings(_env_file=None),
        NoDatabase(),
        identity=identity or FakeIdentity("USER"),
        disputes=disputes or FakeDisputes(),
        orders=orders or FakeOrders(),
    )
    return AsyncClient(transport=ASGITransport(app), base_url="http://test")


async def report(client, payload=None, **headers):
    return await client.post(
        "/v1/disputes",
        json=payload or {"orderId": str(uuid4()), "description": "  Nothing arrived.  "},
        headers={**AUTH, "Idempotency-Key": KEY, **headers},
    )


@pytest.mark.parametrize("role", ["REQUESTER", "COURIER"])
async def test_participant_reports_a_problem_that_starts_open(role):
    disputes, identity = FakeDisputes(), FakeIdentity("USER")
    orders = FakeOrders(participation=(role, "DELIVERED"))
    order_id = str(uuid4())
    async with client_for(disputes, orders, identity) as client:
        response = await report(client, {"orderId": order_id, "description": " Nothing arrived. "})
    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["reporterRole"]) == ("OPEN", role)
    assert body["description"] == "Nothing arrived."
    assert "createdBy" not in body and "history" not in body
    assert orders.calls == [(UUID(order_id), "user-token", identity.user_id)]
    values = disputes.calls[0][1]
    assert (values["reporter"], values["role"], str(values["key"])) == (identity.user_id, role, KEY)


async def test_replaying_a_report_returns_the_original():
    disputes = FakeDisputes()
    disputes.created = False
    async with client_for(disputes) as client:
        response = await report(client)
    assert response.status_code == 200


async def test_non_participants_cannot_tell_whether_the_errand_exists():
    disputes = FakeDisputes()
    async with client_for(disputes, FakeOrders(participation=None)) as client:
        response = await report(client)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "ORDER_NOT_FOUND")
    assert disputes.calls == []


@pytest.mark.parametrize("state", ["OPEN", "CANCELLED", "EXPIRED"])
async def test_reports_need_an_accepted_errand(state):
    disputes = FakeDisputes()
    async with client_for(disputes, FakeOrders(participation=("REQUESTER", state))) as client:
        response = await report(client)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "REPORT_NOT_ALLOWED")
    assert disputes.calls == []


async def test_only_one_open_report_per_errand():
    disputes = FakeDisputes()
    disputes.error = ReportAlreadyOpen()
    async with client_for(disputes) as client:
        response = await report(client)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "REPORT_ALREADY_OPEN")


@pytest.mark.parametrize(
    "payload",
    [
        {"orderId": str(uuid4()), "description": "   "},
        {"orderId": str(uuid4()), "description": "x", "evidenceRefs": ["chat:1"]},
        {"description": "No errand"},
    ],
)
async def test_invalid_reports_are_rejected(payload):
    disputes = FakeDisputes()
    async with client_for(disputes) as client:
        response = await report(client, payload)
    assert response.status_code == 422
    assert disputes.calls == []


async def test_reports_need_a_key_and_a_session():
    async with client_for() as client:
        missing_key = await client.post(
            "/v1/disputes", json={"orderId": str(uuid4()), "description": "x"}, headers=AUTH
        )
        signed_out = await client.post(
            "/v1/disputes",
            json={"orderId": str(uuid4()), "description": "x"},
            headers={"Idempotency-Key": KEY},
        )
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert signed_out.status_code == 401


async def test_users_see_only_their_own_reports_and_their_outcome():
    disputes, identity = FakeDisputes(), FakeIdentity("USER")
    order_id = uuid4()
    resolved = dispute_row(
        order_id=order_id,
        status="RESOLVED",
        resolution_reason="Courier confirmed the mix-up.",
        reporter_role="REQUESTER",
        created_by=identity.user_id,
    )
    disputes.page = ([resolved], 1)
    async with client_for(disputes, identity=identity) as client:
        response = await client.get(f"/v1/disputes?orderId={order_id}", headers=AUTH)
    item = response.json()["items"][0]
    assert (item["status"], item["resolutionReason"]) == (
        "RESOLVED",
        "Courier confirmed the mix-up.",
    )
    assert disputes.calls == [
        ("reports_for", identity.user_id, {"order_id": order_id, "page": 1, "page_size": 20})
    ]
