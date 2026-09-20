"""Strict public DTOs for Phase 1 registration and email verification."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import AccountStatus, ParticipationMode, SystemRole
from app.registration.validation import (
    validate_email,
    validate_otp,
    validate_password,
    validate_profile_name,
    validate_username,
)


def to_camel(value: str) -> str:
    """Expose the documented camelCase JSON contract."""

    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    """Reject unrecognised client fields, including protected identity fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class RegistrationRequest(ApiModel):
    username: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(default=None, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_requested_username(cls, value: str) -> str:
        return validate_username(value)

    @field_validator("email")
    @classmethod
    def validate_requested_email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_requested_password(cls, value: str) -> str:
        return validate_password(value)

    @field_validator("display_name")
    @classmethod
    def validate_requested_display_name(cls, value: str | None) -> str | None:
        return None if value is None else validate_profile_name(value)

    @model_validator(mode="after")
    def default_display_name_to_username(self) -> RegistrationRequest:
        if self.display_name is None:
            self.display_name = self.username
        return self


class EmailVerificationRequest(ApiModel):
    email: str = Field(min_length=3, max_length=254)
    otp: str = Field(min_length=1, max_length=12)

    @field_validator("email")
    @classmethod
    def validate_requested_email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("otp")
    @classmethod
    def validate_requested_otp(cls, value: str) -> str:
        return validate_otp(value)


class EmailResendRequest(ApiModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_requested_email(cls, value: str) -> str:
        return validate_email(value)


class VerificationPendingResponse(ApiModel):
    status: Literal["verification_pending"] = "verification_pending"
    email: str
    expires_at: datetime


class AccountActivatedResponse(ApiModel):
    status: Literal["active"] = "active"
    user_id: UUID
    username: str
    email: str
    display_name: str
    system_role: Literal["USER"] = "USER"
    email_verified_at: datetime


class SessionCreateRequest(ApiModel):
    """Credential payload deliberately kept generic to avoid account enumeration."""

    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AccessSessionResponse(ApiModel):
    """Public token response; the opaque refresh token is cookie-only."""

    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_at: datetime


class CurrentUserResponse(ApiModel):
    """Only the authenticated caller's safe identity and current mode."""

    user_id: UUID
    username: str
    email: str
    display_name: str
    system_role: SystemRole
    account_status: AccountStatus
    active_participation_mode: ParticipationMode
