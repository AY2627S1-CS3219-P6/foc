"""N2F3.7: closing a dispute may fail or complete the errand through Order, safely."""

from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.admin.disputes import ErrandChanged, VersionConflict
from app.admin.errors import ApiError
from app.admin.orders import OrderDirectory
from app.core.config import Settings
from app.main import create_app
from tests.admin_fakes import FakeDisputes, FakeIdentity, FakeOrders, NoDatabase, dispute_row

AUTH = {"Authorization": "Bearer admin-token"}
REASON = "Requester showed nothing arrived."


def client_for(disputes, orders):
    app = create_app(
        Settings(_env_file=None),
        NoDatabase(),
        identity=FakeIdentity(),
        disputes=disputes,
        orders=orders,
    )
    return AsyncClient(transport=ASGITransport(app), base_url="http://test")


def under_review(**changes):
    disputes = FakeDisputes()
    disputes.row = dispute_row(
        status="UNDER_REVIEW", version=2, reporter_role="REQUESTER", **changes
    )
    return disputes


async def decide(disputes, orders, **payload):
    body = {"toStatus": "RESOLVED", "reason": REASON, "expectedVersion": 2, **payload}
    async with client_for(disputes, orders) as client:
        return await client.post(
            f"/v1/admin/disputes/{disputes.row['id']}/transitions", json=body, headers=AUTH
        )


@pytest.mark.parametrize(
    "status,outcome", [("RESOLVED", "FAILED"), ("RESOLVED", "COMPLETED"), ("REJECTED", "COMPLETED")]
)
async def test_closing_with_an_outcome_applies_it_in_order_first(status, outcome):
    disputes, orders = under_review(), FakeOrders()
    dispute_id, order_id = disputes.row["id"], disputes.row["order_id"]
    response = await decide(disputes, orders, toStatus=status, errandOutcome=outcome)
    assert response.status_code == 200
    assert (response.json()["status"], response.json()["errandOutcome"]) == (status, outcome)
    assert orders.calls == [("decide", order_id, outcome, dispute_id, REASON, "admin-token")]
    name, _, values = disputes.calls[-1]
    assert name == "transition" and values["errand_outcome"] == outcome


async def test_closing_without_an_outcome_never_calls_order():
    disputes, orders = under_review(), FakeOrders()
    response = await decide(disputes, orders)
    assert response.status_code == 200 and response.json()["errandOutcome"] is None
    assert orders.calls == []


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"toStatus": "UNDER_REVIEW", "errandOutcome": "FAILED"}, "VALIDATION_ERROR"),
        ({"reason": "x" * 501, "errandOutcome": "FAILED"}, "VALIDATION_ERROR"),
        ({"errandOutcome": "CANCELLED"}, "VALIDATION_ERROR"),
        ({"reason": None, "errandOutcome": "FAILED"}, "REASON_REQUIRED"),
    ],
)
async def test_invalid_outcome_requests_change_nothing(payload, code):
    disputes, orders = under_review(), FakeOrders()
    response = await decide(disputes, orders, **payload)
    assert response.status_code == 422 and response.json()["error"]["code"] == code
    assert orders.calls == [] and not [call for call in disputes.calls if call[0] == "transition"]


@pytest.mark.parametrize(
    "changes,payload,code",
    [
        ({}, {"expectedVersion": 1}, "VERSION_CONFLICT"),
        ({"status": "OPEN", "version": 2}, {}, "INVALID_TRANSITION"),
    ],
)
async def test_errand_is_untouched_unless_the_dispute_can_close(changes, payload, code):
    disputes, orders = under_review(), FakeOrders()
    disputes.row = {**disputes.row, **changes}
    response = await decide(disputes, orders, errandOutcome="FAILED", **payload)
    assert (response.status_code, response.json()["error"]["code"]) == (409, code)
    assert orders.calls == []


async def test_errand_changed_in_order_leaves_the_dispute_under_review():
    disputes, orders = under_review(), FakeOrders(error=ErrandChanged())
    response = await decide(disputes, orders, errandOutcome="COMPLETED")
    assert (response.status_code, response.json()["error"]["code"]) == (409, "ERRAND_CHANGED")
    assert not [call for call in disputes.calls if call[0] == "transition"]
    assert {rejection["action"] for rejection in disputes.rejections} >= {"ERRAND_DECISION"}


async def test_dispute_close_failing_after_the_errand_changed_says_so():
    disputes, orders = under_review(), FakeOrders()
    disputes.error = VersionConflict()
    response = await decide(disputes, orders, errandOutcome="FAILED")
    assert (response.status_code, response.json()["error"]["code"]) == (409, "DECISION_INCOMPLETE")
    assert len(orders.calls) == 1


async def test_participants_see_the_errand_outcome_of_their_report():
    disputes, identity = FakeDisputes(), FakeIdentity("USER")
    order_id = uuid4()
    disputes.page = (
        [
            dispute_row(
                order_id=order_id,
                status="RESOLVED",
                resolution_reason=REASON,
                errand_outcome="FAILED",
                reporter_role="REQUESTER",
                created_by=identity.user_id,
            )
        ],
        1,
    )
    app = create_app(
        Settings(_env_file=None),
        NoDatabase(),
        identity=identity,
        disputes=disputes,
        orders=FakeOrders(),
    )
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        response = await client.get(f"/v1/disputes?orderId={order_id}", headers=AUTH)
    assert response.json()["items"][0]["errandOutcome"] == "FAILED"


def directory(handler):
    settings = Settings(_env_file=None, order_service_base_url="http://order-service:8002")
    return OrderDirectory(settings, httpx.AsyncClient(transport=httpx.MockTransport(handler)))


@pytest.mark.parametrize(
    "outcome,path,body",
    [
        ("FAILED", "fail", {"disputeId": "{dispute}", "reason": REASON}),
        ("COMPLETED", "complete", {"disputeId": "{dispute}"}),
    ],
)
async def test_order_client_posts_the_decision_with_the_admin_token(outcome, path, body):
    order_id, dispute_id, seen = uuid4(), uuid4(), {}

    def handler(request):
        seen.update(url=str(request.url), auth=request.headers["Authorization"])
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={})

    await directory(handler).decide(order_id, outcome, dispute_id, REASON, "abc")
    assert seen["url"] == f"http://order-service:8002/v1/admin/orders/{order_id}/{path}"
    assert seen["auth"] == "Bearer abc"
    expected = {key: value.replace("{dispute}", str(dispute_id)) for key, value in body.items()}
    assert httpx.Response(200, content=seen["body"]).json() == expected


@pytest.mark.parametrize(
    "status,code", [(409, "ERRAND_CHANGED"), (404, "ORDER_NOT_FOUND"), (500, "ORDER_UNAVAILABLE")]
)
async def test_order_client_maps_decision_failures(status, code):
    with pytest.raises(ApiError) as error:
        await directory(lambda request: httpx.Response(status)).decide(
            uuid4(), "FAILED", uuid4(), REASON, "abc"
        )
    assert error.value.code == code
