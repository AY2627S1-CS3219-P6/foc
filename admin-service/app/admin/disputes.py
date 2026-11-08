# AI Assistance Disclosure:
# Tool: Claude Code (model: Claude Opus 5.5), date: 2026-10-28, 2026-10-29, 2026-11-08
# Scope: Implemented dispute workflow rules, request fingerprints and safe rejections; added
# participant report and errand outcome errors.
# Author review: I validated correctness and supplied additional boundary checks.

"""Dispute workflow rules (N2F3.3) and safe rejections. Messages never echo input."""

import hashlib
import json

from app.admin.errors import ApiError

TRANSITIONS = {"OPEN": ("UNDER_REVIEW",), "UNDER_REVIEW": ("RESOLVED", "REJECTED")}
FINAL_STATUSES = ("RESOLVED", "REJECTED")
# Participants can report once a courier is involved: from acceptance onwards.
REPORTABLE_STATES = ("ACCEPTED", "PICKED_UP", "DELIVERED", "COMPLETED", "FAILED")


class ReportNotAllowed(ApiError):
    def __init__(self):
        super().__init__(
            409, "REPORT_NOT_ALLOWED", "Problems can be reported once a courier accepts the errand."
        )


class ReportAlreadyOpen(ApiError):
    def __init__(self):
        super().__init__(
            409, "REPORT_ALREADY_OPEN", "You already have an open report about this errand."
        )


class DisputeNotFound(ApiError):
    def __init__(self):
        super().__init__(404, "DISPUTE_NOT_FOUND", "The dispute does not exist.")


class OrderNotFound(ApiError):
    def __init__(self):
        super().__init__(422, "ORDER_NOT_FOUND", "The errand does not exist.")


class ErrandChanged(ApiError):
    def __init__(self):
        super().__init__(
            409,
            "ERRAND_CHANGED",
            "The errand changed, so this outcome is no longer possible. Refresh and decide again.",
        )


class DecisionIncomplete(ApiError):
    def __init__(self):
        super().__init__(
            409,
            "DECISION_INCOMPLETE",
            "The errand outcome was applied, but the dispute was not closed. "
            "Refresh and close it with the same outcome.",
        )


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
