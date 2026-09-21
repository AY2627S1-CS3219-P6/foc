from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import AccountDeletionRequest, ProfileUpdateRequest


def test_profile_update_accepts_only_mutable_validated_fields() -> None:
    request = ProfileUpdateRequest.model_validate({"displayName": "Updated_User?"})

    assert request.display_name == "Updated_User?"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"displayName": "Invalid display name"},
        {"displayName": None},
        {"email": "replacement@u.nus.edu"},
        {"username": "replacement"},
        {"activeParticipationMode": "COURIER"},
        {"systemRole": "ADMIN"},
        {"accountStatus": "SUSPENDED"},
        {"id": "00000000-0000-0000-0000-000000000001"},
    ],
)
def test_profile_update_rejects_empty_invalid_and_protected_changes(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"currentPassword": "SecurePass1!", "acknowledgeDeletion": False},
        {"currentPassword": "SecurePass1!", "acknowledgeDeletion": True, "email": "x@u.nus.edu"},
    ],
)
def test_account_deletion_requires_password_and_explicit_acknowledgement(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AccountDeletionRequest.model_validate(payload)


def test_account_deletion_accepts_a_true_explicit_acknowledgement() -> None:
    request = AccountDeletionRequest.model_validate(
        {"currentPassword": "SecurePass1!", "acknowledgeDeletion": True}
    )

    assert request.current_password == "SecurePass1!"
    assert request.acknowledge_deletion is True
