from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import RegistrationRequest


def test_registration_defaults_display_name_to_username() -> None:
    request = RegistrationRequest(
        username="Alice_User?",
        email="alice@u.nus.edu",
        password="SecurePass1!",
    )

    assert request.display_name == "Alice_User?"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("username", "Alice User", "Username may contain only"),
        ("email", "alice@example.com", "Use a NUS student email address"),
        ("password", "onlylowercasepassword", "at least three"),
        ("password", "Short1!", "at least 12"),
        ("password", "Secure Pass1!", "may contain only"),
        ("display_name", "Alice User", "Display name may contain only"),
    ],
)
def test_registration_rejects_values_outside_backlog_rules(
    field: str,
    value: str,
    message: str,
) -> None:
    payload = {
        "username": "Alice_User?",
        "email": "alice@u.nus.edu",
        "password": "SecurePass1!",
        "display_name": "Alice_User?",
    }
    payload[field] = value

    with pytest.raises(ValidationError, match=message):
        RegistrationRequest.model_validate(payload)
