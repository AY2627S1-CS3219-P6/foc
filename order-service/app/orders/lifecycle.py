"""OPEN-state transition rules, evaluated against a locked row and database time."""

from collections.abc import Mapping
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.orders.errors import ApiError, not_found

Action = Literal["accept", "cancel"]


def transition_values(order: Mapping, actor: UUID, action: Action, now: datetime) -> dict:
    """Return a change, or an empty mapping for an authorized successful replay."""
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
