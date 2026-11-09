# AI Assistance Disclosure:
# Tool: ChatGPT (Codex, model: gpt-6-astra), date: 2026-10-11
# Tool: ChatGPT (Codex, model: gpt-6.1-sol), date: 2026-10-11
# Scope: Implemented participant acceptance, cancellation, expiry, fulfilment and failure
# actions.
# Author review: I validated correctness and added boundary checks where needed.

"""Lifecycle rules evaluated against a locked row and database time."""

from collections.abc import Mapping
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.orders.errors import ApiError, not_found

Action = Literal["accept", "cancel", "pickup", "deliver", "complete", "fail"]
AdminAction = Literal["fail", "complete"]

# N2F3.7: what an administrator deciding a dispute may do. COMPLETED errands have already paid
# the courier, so they are never reversed here.
ADMIN_SOURCES = {
    "fail": ({"ACCEPTED", "PICKED_UP", "DELIVERED"}, "FAILED"),
    "complete": ({"DELIVERED"}, "COMPLETED"),
}

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


def admin_decision_values(
    order: Mapping,
    admin: UUID,
    action: AdminAction,
    now: datetime,
    dispute_id: UUID,
    reason: str | None = None,
) -> dict:
    """Return the decided change, or an empty mapping when the same decision is replayed."""
    sources, target = ADMIN_SOURCES[action]
    if order["state"] == target and order.get("decision_dispute_id") == dispute_id:
        # A retry for the same dispute succeeds without recording anything again.
        return {}
    if order["state"] not in sources:
        outcome = "failed" if action == "fail" else "completed"
        raise ApiError(
            409, "INVALID_TRANSITION", f"This errand has changed and can no longer be {outcome}."
        )
    decision = {"decided_by": admin, "decision_dispute_id": dispute_id}
    if action == "complete":
        return {"state": "COMPLETED", "completed_at": now, **decision}
    if not reason:
        raise ValueError("An administrator failure requires a validated reason")
    return {
        "state": "FAILED",
        "failed_at": now,
        "failed_by": admin,
        "failure_reason": "ADMIN_DECISION",
        "failure_details": reason,
        **decision,
        **overdue_values(order, now),
    }


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
