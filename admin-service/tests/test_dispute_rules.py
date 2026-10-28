"""N2F3.3.1-N2F3.3.3 workflow rules and N2NFR3.3 request fingerprints."""

from uuid import uuid4

import pytest

from app.admin.disputes import (
    InvalidTransition,
    ReasonRequired,
    check_transition,
    request_fingerprint,
)


@pytest.mark.parametrize(
    "current,target",
    [("OPEN", "UNDER_REVIEW"), ("UNDER_REVIEW", "RESOLVED"), ("UNDER_REVIEW", "REJECTED")],
)
def test_allowed_transitions(current, target):
    check_transition(current, target, "Checked the chat and the courier's photo.")


@pytest.mark.parametrize(
    "current,target",
    [
        ("OPEN", "RESOLVED"),
        ("OPEN", "REJECTED"),
        ("OPEN", "OPEN"),
        ("UNDER_REVIEW", "OPEN"),
        ("UNDER_REVIEW", "UNDER_REVIEW"),
        ("RESOLVED", "REJECTED"),
        ("RESOLVED", "UNDER_REVIEW"),
        ("REJECTED", "RESOLVED"),
    ],
)
def test_other_transitions_are_rejected(current, target):
    with pytest.raises(InvalidTransition):
        check_transition(current, target, "A reason")


@pytest.mark.parametrize("target", ["RESOLVED", "REJECTED"])
@pytest.mark.parametrize("reason", [None, ""])
def test_closing_requires_a_reason(target, reason):
    with pytest.raises(ReasonRequired):
        check_transition("UNDER_REVIEW", target, reason)


def test_starting_a_review_needs_no_reason():
    check_transition("OPEN", "UNDER_REVIEW", None)


def test_fingerprint_changes_with_any_recorded_field():
    order_id = uuid4()
    original = request_fingerprint(order_id, "Nothing arrived.", ["chat:1"])
    assert original == request_fingerprint(order_id, "Nothing arrived.", ["chat:1"])
    assert original != request_fingerprint(uuid4(), "Nothing arrived.", ["chat:1"])
    assert original != request_fingerprint(order_id, "Nothing arrived!", ["chat:1"])
    assert original != request_fingerprint(order_id, "Nothing arrived.", [])
