"""Versioned public schemas and typed dependency responses."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")


class CreateOrder(ApiModel):
    supplier_id: UUID
    item_description: str = Field(min_length=1, max_length=1000)
    delivery_location: str = Field(min_length=1, max_length=300)
    reward: StrictInt = Field(gt=0, le=2_147_483_647)
    acceptance_deadline: AwareDatetime
    delivery_deadline: AwareDatetime

    @field_validator("item_description", "delivery_location", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("acceptance_deadline", "delivery_deadline", mode="before")
    @classmethod
    def require_iso_time(cls, value):
        if not isinstance(value, str):
            raise ValueError("Use an ISO 8601 timestamp with a timezone offset")
        return value

    @field_validator("acceptance_deadline", "delivery_deadline")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def deadline_order(self):
        if self.delivery_deadline <= self.acceptance_deadline:
            raise ValueError("Delivery deadline must be later than acceptance deadline")
        return self


class PageQuery(ApiModel):
    page: int = Field(default=1, ge=1, le=1_000_000)
    page_size: int = Field(default=20, ge=1, le=50)


class OpenQuery(PageQuery):
    supplier_id: UUID | None = None


class OwnQuery(PageQuery):
    relationship: Literal["requester", "courier"]


class AdminQuery(PageQuery):
    requester_id: UUID


class Principal(BaseModel):
    # User's additional profile fields are deliberately ignored, never persisted.
    model_config = ConfigDict(alias_generator=to_camel, extra="ignore")
    user_id: UUID
    system_role: Literal["USER", "ADMIN", "SUPER_ADMIN"]
    account_status: Literal["ACTIVE"]


class SupplierSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    name: str = Field(min_length=1)
    building_area: str = Field(min_length=1)
    pickup_location_description: str = Field(min_length=1)
    floor: str | None
    latitude: float | None = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(ge=-180, le=180, allow_inf_nan=False)
    updated_at: AwareDatetime
    status: Literal["ACTIVE"]

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Coordinates must be paired")
        return self

    def snapshot(self) -> dict:
        values = self.model_dump(mode="json", exclude={"id", "status"})
        return {to_camel(key): value for key, value in values.items()}


class Reservation(ApiModel):
    operation_id: UUID
    order_id: UUID
    requester_id: UUID
    amount: StrictInt = Field(gt=0)
    reservation_id: UUID | None
    state: Literal["RESERVED", "RELEASED", "TRANSFERRED", "CLOSED"]

    @model_validator(mode="after")
    def require_reservation(self):
        if self.state != "CLOSED" and self.reservation_id is None:
            raise ValueError("Reservation identity required")
        return self


OrderState = Literal[
    "OPEN", "ACCEPTED", "PICKED_UP", "DELIVERED", "COMPLETED", "CANCELLED", "EXPIRED", "FAILED"
]


class Pickup(ApiModel):
    name: str
    building_area: str
    pickup_location_description: str
    floor: str | None
    latitude: float | None
    longitude: float | None
    updated_at: AwareDatetime


class OrderAssessment(ApiModel):
    order_id: UUID
    supplier_id: UUID
    pickup: Pickup
    item_description: str
    delivery_location: str
    reward: int
    state: OrderState
    acceptance_deadline: AwareDatetime
    delivery_deadline: AwareDatetime
    created_at: AwareDatetime


class OrderParticipant(OrderAssessment):
    requester_id: UUID
    courier_id: UUID | None
    updated_at: AwareDatetime


class CreationResponse(ApiModel):
    operation_id: UUID
    stage: Literal[
        "VALIDATED", "RESERVATION_UNKNOWN", "READY_TO_FINALIZE", "SUCCEEDED", "ABORTING", "ABORTED"
    ]
    status_url: str
    retry_creation: bool
    error_code: str | None
    order_id: UUID | None = None


class HistoryEntry(ApiModel):
    sequence: int
    previous_state: OrderState | None
    new_state: OrderState
    actor_id: UUID
    actor_type: Literal["USER", "SYSTEM"]
    occurred_at: AwareDatetime


class Page[T](ApiModel):
    items: list[T]
    page: int
    page_size: int
    total: int
