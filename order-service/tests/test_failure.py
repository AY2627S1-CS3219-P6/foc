from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.orders.errors import ApiError
from app.orders.lifecycle import transition_values
from app.orders.outbox import event_payload
from app.orders.schemas import FailOrder
from tests.test_fulfilment import COURIER, NOW, OWNER, row
from tests.test_lifecycle import api as _api  # noqa: F401

REPORT = {"reason": "ITEM_DAMAGED", "details": "Item damaged after pickup"}


@pytest.mark.parametrize("state", ["ACCEPTED", "PICKED_UP"])
@pytest.mark.parametrize("actor", [OWNER, COURIER])
def test_either_participant_fails_without_agreement_and_replays(state, actor):
    original = row(state=state)
    values = transition_values(original, actor, "fail", NOW, REPORT)
    assert values["state"] == "FAILED" and values["failed_by"] == actor
    assert values["failed_at"] == NOW and values["failure_reason"] == REPORT["reason"]
    assert original["state"] == state
    assert transition_values({**original, **values}, actor, "fail", NOW, REPORT) == {}


@pytest.mark.parametrize("state", ["OPEN", "DELIVERED", "COMPLETED", "CANCELLED", "EXPIRED"])
def test_failure_cannot_skip_or_reverse_lifecycle(state):
    with pytest.raises(ApiError, match="INVALID_TRANSITION"):
        transition_values(row(state=state), OWNER, "fail", NOW, REPORT)


def test_unrelated_actor_cannot_fail_or_replay():
    original = row()
    failed = {**original, **transition_values(original, OWNER, "fail", NOW, REPORT)}
    for order in (original, failed):
        with pytest.raises(ApiError) as error:
            transition_values(order, uuid4(), "fail", NOW, REPORT)
        assert error.value.status == 404


@pytest.mark.parametrize(
    "actor,report",
    [
        (COURIER, REPORT),
        (OWNER, {**REPORT, "reason": "OTHER"}),
        (OWNER, {**REPORT, "details": "Different incident"}),
    ],
)
def test_competing_or_edited_failure_does_not_overwrite_original(actor, report):
    original = row()
    failed = {**original, **transition_values(original, OWNER, "fail", NOW, REPORT)}
    with pytest.raises(ApiError, match="FAILURE_CONFLICT"):
        transition_values(failed, actor, "fail", NOW, report)


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_failure_keeps_overdue_deadline_without_later_marking(offset):
    deadline = NOW + timedelta(seconds=offset)
    original = row(delivery_deadline=deadline)
    values = transition_values(original, OWNER, "fail", NOW, REPORT)
    assert values.get("overdue_at") == (deadline if offset <= 0 else None)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"reason": "UNKNOWN"},
        {"reason": "OTHER"},
        {"reason": "OTHER", "details": " "},
        {"reason": "ITEM_DAMAGED", "details": "x" * 501},
        {"reason": "ITEM_DAMAGED", "details": 42},
        {**REPORT, "actorId": str(OWNER)},
        {**REPORT, "penalty": 5},
        {**REPORT, "state": "FAILED"},
    ],
)
def test_failure_input_rejects_invalid_and_protected_fields(body):
    with pytest.raises(ValidationError):
        FailOrder.model_validate(body)


def test_details_are_trimmed_and_optional_except_other():
    assert (
        FailOrder.model_validate({"reason": "OTHER", "details": "  broken  "}).details == "broken"
    )
    assert FailOrder.model_validate({"reason": "ITEM_UNAVAILABLE"}).details is None


async def test_failure_uses_fresh_auth_and_never_has_admin_bypass(api):
    http, clients, lifecycle = api
    path = f"/v1/orders/{uuid4()}/fail"
    assert (await http.post(path, json=REPORT)).status_code == 401
    clients.auth_error = ApiError(503, "AUTH_UNAVAILABLE", "Unavailable")
    headers = {"Authorization": "Bearer token"}
    assert (await http.post(path, json=REPORT, headers=headers)).status_code == 503
    lifecycle.transition.assert_not_awaited()
    clients.auth_error = None
    clients.role = "SUPER_ADMIN"
    lifecycle.transition.side_effect = ApiError(404, "NOT_FOUND", "Unavailable")
    assert (await http.post(path, json=REPORT, headers=headers)).status_code == 404


async def test_failure_body_and_queries_validated_before_mutation(api):
    http, _, lifecycle = api
    path, headers = f"/v1/orders/{uuid4()}/fail", {"Authorization": "Bearer token"}
    for body in ({}, {**REPORT, "actorId": str(OWNER)}, {"reason": "OTHER"}, []):
        assert (await http.post(path, json=body, headers=headers)).status_code == 422
    assert (await http.post(path + "?actorId=bad", json=REPORT, headers=headers)).status_code == 422
    lifecycle.transition.assert_not_awaited()


def test_failure_event_excludes_reason_details_actor_and_penalty():
    event = {
        "event_id": uuid4(),
        "event_type": "order.failed.v1",
        "order_id": uuid4(),
        "reservation_id": uuid4(),
        "occurred_at": NOW,
        "failure_reason": "ITEM_DAMAGED",
        "failure_details": "Private incident",
        "failed_by": OWNER,
    }
    assert set(event_payload(event)) == {
        "eventId",
        "eventType",
        "orderId",
        "reservationId",
        "occurredAt",
    }
