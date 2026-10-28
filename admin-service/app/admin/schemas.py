"""Versioned API models. JSON uses camelCase; Python uses snake_case."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, field_validator
from pydantic.alias_generators import to_camel


class Principal(BaseModel):
    # User's additional profile fields are deliberately ignored, never persisted.
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore", populate_by_name=True)
    user_id: UUID
    system_role: Literal["USER", "ADMIN", "SUPER_ADMIN"]
    account_status: Literal["ACTIVE"]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid", populate_by_name=True)


DisputeStatus = Literal["OPEN", "UNDER_REVIEW", "RESOLVED", "REJECTED"]
EvidenceRef = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def trimmed(value):
    return value.strip() if isinstance(value, str) else value


class CreateDispute(ApiModel):
    order_id: UUID
    # N2F3.2.1: non-blank after trimming; evidence references are optional.
    description: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=10)

    @field_validator("description", mode="before")
    @classmethod
    def trim_description(cls, value):
        return trimmed(value)


class Transition(ApiModel):
    to_status: Literal["UNDER_REVIEW", "RESOLVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=1000)
    expected_version: StrictInt = Field(ge=1)

    @field_validator("reason", mode="before")
    @classmethod
    def blank_reason_is_missing(cls, value):
        return trimmed(value) or None


class PageQuery(ApiModel):
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=20, ge=1, le=50)


class DisputeQuery(PageQuery):
    status: DisputeStatus | None = None
    order_id: UUID | None = None


class AuditQuery(PageQuery):
    actor_id: UUID | None = None
    target_id: UUID | None = None
    outcome: Literal["SUCCESS", "REJECTED"] | None = None


class HistoryEntry(ApiModel):
    sequence: int
    from_status: DisputeStatus | None
    to_status: DisputeStatus
    actor_id: UUID
    reason: str | None
    occurred_at: datetime


class DisputeSummary(ApiModel):
    dispute_id: UUID
    order_id: UUID
    description: str
    status: DisputeStatus
    resolution_reason: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    version: int


class DisputeView(DisputeSummary):
    evidence_refs: list[str]
    history: list[HistoryEntry]


class AuditEntry(ApiModel):
    audit_id: UUID
    actor_id: UUID
    action: Literal["DISPUTE_CREATE", "DISPUTE_TRANSITION"]
    target_type: Literal["DISPUTE", "ORDER"]
    target_id: UUID
    outcome: Literal["SUCCESS", "REJECTED"]
    error_code: str | None
    correlation_id: str
    occurred_at: datetime


class Page[T](ApiModel):
    items: list[T]
    page: int
    page_size: int
    total: int
