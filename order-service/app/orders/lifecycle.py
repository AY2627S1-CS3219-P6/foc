"""Lifecycle rules evaluated against a locked row and database time."""

from collections.abc import Mapping
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.orders.errors import ApiError, not_found

Action = Literal["accept", "cancel", "pickup", "deliver", "complete", "fail"]

FULFILMENT = {
    "pickup": ("ACCEPTED", "PICKED_UP", "picked_up_at", "courier_id"),
    "deliver": ("PICKED_UP", "DELIVERED", "delivered_at", "courier_id"),
    "complete": ("DELIVERED", "COMPLETED", "completed_at", "requester_id"),
}


def overdue_values(order: Mapping, now: datetime) -> dict:
    if (
        order["state"] in {"ACCEPTED", "PICKED_UP"}
        and order.get("overdue_at") is None
        and now >= order["delivery_deadline"]
    ):
        return {"overdue_at": order["delivery_deadline"]}
    return {}


def transition_values(
    order: Mapping, actor: UUID, action: Action, now: datetime, failure: Mapping | None = None
) -> dict:
    """Return a change, or an empty mapping for an authorized successful replay."""
    if action == "fail":
        if actor not in (order["requester_id"], order["courier_id"]):
            raise not_found()
        if failure is None:
            raise ValueError("Failure requires a validated reason")
        if order["state"] == "FAILED":
            if (
                order["failed_by"] == actor
                and order["failure_reason"] == failure["reason"]
                and order["failure_details"] == failure.get("details")
            ):
                return {}
            raise ApiError(409, "FAILURE_CONFLICT", "A different failure is already recorded.")
        if order["state"] not in {"ACCEPTED", "PICKED_UP"}:
            raise ApiError(
                409, "INVALID_TRANSITION", "Failure requires ACCEPTED or PICKED_UP state."
            )
        return {
            "state": "FAILED",
            "failed_at": now,
            "failed_by": actor,
            "failure_reason": failure["reason"],
            "failure_details": failure.get("details"),
            **overdue_values(order, now),
        }
    if action in FULFILMENT:
        source, target, timestamp, actor_column = FULFILMENT[action]
        if actor not in (order["requester_id"], order["courier_id"]):
            raise not_found()
        if order[actor_column] != actor:
            raise ApiError(403, "FORBIDDEN", "Only the designated participant may do this action.")
        if order.get(timestamp) is not None:
            # A prior successful action stays successful; replay never reverses state.
            return {}
        if order["state"] != source:
            raise ApiError(409, "INVALID_TRANSITION", f"This action requires {source} state.")
        return {"state": target, timestamp: now, **overdue_values(order, now)}
    if action == "cancel":
        if order["requester_id"] != actor:
            raise not_found()
        if order["state"] == "CANCELLED":
            return {}
    elif action == "accept":
        if order["requester_id"] == actor:
            raise ApiError(403, "SELF_ACCEPTANCE", "You cannot accept your own errand.")
        if order["courier_id"] == actor and order.get("accepted_at") is not None:
            # Acceptance remains a successful fact even if fulfilment later advances.
            return {}
    else:
        raise ValueError("Unsupported lifecycle action")
    if order["state"] != "OPEN":
        raise ApiError(409, "ORDER_NOT_OPEN", "This errand is no longer open.")
    if now >= order["acceptance_deadline"]:
        raise ApiError(409, "DEADLINE_PASSED", "The acceptance deadline has passed.")
    if action == "accept":
        return {"state": "ACCEPTED", "courier_id": actor, "accepted_at": now}
    return {"state": "CANCELLED", "cancelled_at": now}
