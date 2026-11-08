"""N2F3.7: administrators deciding a dispute may fail or complete an errand, nothing more."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.orders.errors import ApiError
from app.orders.lifecycle import admin_decision_values
from app.orders.schemas import FailOrder
from tests.order_fakes import FakeClients, MemoryRepository
from tests.test_admin_orders import BASE, errand
from tests.test_fulfilment import NOW, row

ADMIN, DISPUTE = uuid4(), uuid4()
REASON = "Requester showed the errand never arrived."


@pytest.mark.parametrize("state", ["ACCEPTED", "PICKED_UP", "DELIVERED"])
def test_administrator_fails_an_accepted_errand_for_a_dispute(state):
    values = admin_decision_values(row(state=state), ADMIN, "fail", NOW, DISPUTE, REASON)
    assert values["state"] == "FAILED" and values["failed_at"] == NOW
    assert (values["failed_by"], values["decided_by"]) == (ADMIN, ADMIN)
    assert (values["failure_reason"], values["failure_details"]) == ("ADMIN_DECISION", REASON)
    assert values["decision_dispute_id"] == DISPUTE


def test_administrator_completes_only_a_delivered_errand():
    values = admin_decision_values(row(state="DELIVERED"), ADMIN, "complete", NOW, DISPUTE)
    assert values == {
        "state": "COMPLETED",
        "completed_at": NOW,
        "decided_by": ADMIN,
        "decision_dispute_id": DISPUTE,
    }


@pytest.mark.parametrize(
    "action,state",
    [
        ("fail", "OPEN"),
        ("fail", "COMPLETED"),
        ("fail", "CANCELLED"),
        ("fail", "EXPIRED"),
        ("complete", "ACCEPTED"),
        ("complete", "PICKED_UP"),
        ("complete", "FAILED"),
        ("complete", "OPEN"),
    ],
)
def test_decisions_never_skip_or_reverse_the_lifecycle(action, state):
    # COMPLETED has already paid the courier, so failing it is never allowed here.
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        admin_decision_values(row(state=state), ADMIN, action, NOW, DISPUTE, REASON)


@pytest.mark.parametrize("action", ["fail", "complete"])
def test_retrying_the_same_dispute_decision_changes_nothing(action):
    original = row(state="DELIVERED")
    decided = {**original, **admin_decision_values(original, ADMIN, action, NOW, DISPUTE, REASON)}
    assert admin_decision_values(decided, uuid4(), action, NOW, DISPUTE, REASON) == {}


def test_a_decided_errand_rejects_another_dispute_or_the_opposite_outcome():
    original = row(state="DELIVERED")
    failed = {**original, **admin_decision_values(original, ADMIN, "fail", NOW, DISPUTE, REASON)}
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        admin_decision_values(failed, ADMIN, "fail", NOW, uuid4(), REASON)
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        admin_decision_values(failed, ADMIN, "complete", NOW, DISPUTE)


def test_participants_cannot_claim_an_administrator_failure():
    with pytest.raises(ValidationError):
        FailOrder.model_validate({"reason": "ADMIN_DECISION", "details": "x"})


def decided_row(repository, requester, courier):
    order_id = errand(
        repository, created_at=BASE, state="FAILED", requester=requester, courier=courier
    )
    repository.rows[order_id].update(
        accepted_at=BASE,
        failed_at=BASE,
        failed_by=ADMIN,
        failure_reason="ADMIN_DECISION",
        failure_details=REASON,
        decided_by=ADMIN,
        decision_dispute_id=DISPUTE,
    )
    repository.histories[order_id].append(
        dict(
            sequence=2,
            previous_state="DELIVERED",
            new_state="FAILED",
            actor_id=ADMIN,
            actor_type="ADMIN",
            occurred_at=BASE,
            failure_reason="ADMIN_DECISION",
            failure_details=REASON,
            dispute_id=DISPUTE,
        )
    )
    return order_id


@pytest.fixture
async def service():
    clients = FakeClients(ADMIN)
    clients.role = "ADMIN"
    repository, lifecycle = MemoryRepository(), AsyncMock()
    app = create_app(
        Settings(_env_file=None),
        clients=clients,
        repository=repository,
        lifecycle_repository=lifecycle,
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app),
            base_url="http://test",
            headers={"Authorization": "Bearer test-only"},
        ) as http:
            yield http, clients, repository, lifecycle


async def test_fail_and_complete_reach_the_locked_decision_path(service):
    http, _, repository, lifecycle = service
    order_id = decided_row(repository, uuid4(), uuid4())
    lifecycle.decide.return_value = repository.rows[order_id]
    failed = await http.post(
        f"/v1/admin/orders/{order_id}/fail",
        json={"disputeId": str(DISPUTE), "reason": f"  {REASON}  "},
    )
    assert failed.status_code == 200
    body = failed.json()
    assert (body["state"], body["failureReason"], body["decidedBy"]) == (
        "FAILED",
        "ADMIN_DECISION",
        str(ADMIN),
    )
    assert body["decidedByAdministrator"] is True
    lifecycle.decide.assert_awaited_with(order_id, ADMIN, "fail", dispute_id=DISPUTE, reason=REASON)
    completed = await http.post(
        f"/v1/admin/orders/{order_id}/complete", json={"disputeId": str(DISPUTE)}
    )
    assert completed.status_code == 200
    lifecycle.decide.assert_awaited_with(order_id, ADMIN, "complete", dispute_id=DISPUTE)


@pytest.mark.parametrize("action", ["fail", "complete"])
async def test_only_current_administrators_decide(service, action):
    http, clients, _, lifecycle = service
    clients.role = "USER"
    body = {"disputeId": str(DISPUTE), **({"reason": REASON} if action == "fail" else {})}
    response = await http.post(f"/v1/admin/orders/{uuid4()}/{action}", json=body)
    assert (response.status_code, response.json()["error"]["code"]) == (403, "FORBIDDEN")
    lifecycle.decide.assert_not_called()


@pytest.mark.parametrize(
    "path,body",
    [
        ("fail", {"reason": REASON}),
        ("fail", {"disputeId": str(DISPUTE)}),
        ("fail", {"disputeId": str(DISPUTE), "reason": "   "}),
        ("fail", {"disputeId": str(DISPUTE), "reason": "x" * 501}),
        ("fail", {"disputeId": str(DISPUTE), "reason": REASON, "failureReason": "OTHER"}),
        ("complete", {}),
        ("complete", {"disputeId": str(DISPUTE), "state": "COMPLETED"}),
        ("complete?force=true", {"disputeId": str(DISPUTE)}),
    ],
)
async def test_decision_input_is_validated(service, path, body):
    http, _, _, lifecycle = service
    response = await http.post(f"/v1/admin/orders/{uuid4()}/{path}", json=body)
    assert response.status_code == 422
    lifecycle.decide.assert_not_called()


async def test_participants_never_learn_which_administrator_decided(service):
    http, clients, repository, _ = service
    requester = uuid4()
    order_id = decided_row(repository, requester, uuid4())
    clients.role, clients.actor = "USER", requester
    detail = (await http.get(f"/v1/orders/{order_id}")).json()
    assert detail["decidedByAdministrator"] is True
    assert detail["decisionDisputeId"] == str(DISPUTE)
    assert (detail["failedBy"], detail["decidedBy"]) == (None, None)
    entry = (await http.get(f"/v1/orders/{order_id}/history")).json()["items"][-1]
    assert (entry["actorType"], entry["actorId"], entry["disputeId"]) == (
        "ADMIN",
        None,
        str(DISPUTE),
    )

    clients.role, clients.actor = "ADMIN", ADMIN
    admin_entry = (await http.get(f"/v1/admin/orders/{order_id}/history")).json()["items"][-1]
    assert admin_entry["actorId"] == str(ADMIN)
