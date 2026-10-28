"""Dispute workflow rules (N2F3.3) and safe rejections. Messages never echo input."""

import hashlib
import json

from app.admin.errors import ApiError

TRANSITIONS = {"OPEN": ("UNDER_REVIEW",), "UNDER_REVIEW": ("RESOLVED", "REJECTED")}
FINAL_STATUSES = ("RESOLVED", "REJECTED")


class DisputeNotFound(ApiError):
    def __init__(self):
        super().__init__(404, "DISPUTE_NOT_FOUND", "The dispute does not exist.")


class OrderNotFound(ApiError):
    def __init__(self):
        super().__init__(422, "ORDER_NOT_FOUND", "The errand does not exist.")


class InvalidTransition(ApiError):
    def __init__(self):
        super().__init__(
            409, "INVALID_TRANSITION", "This status change is not allowed from the current status."
        )


class ReasonRequired(ApiError):
    def __init__(self):
        super().__init__(422, "REASON_REQUIRED", "Give a reason to resolve or reject a dispute.")


class VersionConflict(ApiError):
    def __init__(self):
        super().__init__(
            409,
            "VERSION_CONFLICT",
            "This dispute was changed by someone else. Refresh and review it before retrying.",
        )


class IdempotencyKeyReused(ApiError):
    def __init__(self):
        super().__init__(
            409, "IDEMPOTENCY_KEY_REUSED", "This request key was already used for another dispute."
        )


def check_transition(current: str, target: str, reason: str | None) -> None:
    """OPEN -> UNDER_REVIEW -> RESOLVED | REJECTED; closing needs a non-blank reason."""
    if target not in TRANSITIONS.get(current, ()):
        raise InvalidTransition()
    if target in FINAL_STATUSES and not reason:
        raise ReasonRequired()


def request_fingerprint(order_id, description: str, evidence_refs: list[str]) -> str:
    """Detects a reused idempotency key carrying a different dispute (N2NFR3.3)."""
    canonical = json.dumps(
        [str(order_id), description, evidence_refs], separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
