"""Query metadata only. Supabase SQL migrations exclusively own the schema."""

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData(schema="order_service")

operations = Table(
    "creation_operations",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("order_id", UUID, nullable=False),
    Column("requester_id", UUID, nullable=False),
    Column("key_hash", String(64), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("supplier_snapshot", JSONB, nullable=False),
    Column("stage", Text, nullable=False),
    Column("reservation_id", UUID),
    Column("error_code", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("acceptance_deadline", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("lease_token", UUID),
    Column("lease_until", DateTime(timezone=True)),
    Column("next_attempt_at", DateTime(timezone=True), nullable=False),
    Column("attempts", Integer, nullable=False),
)

orders = Table(
    "orders",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("requester_id", UUID, nullable=False),
    Column("courier_id", UUID),
    Column("supplier_id", UUID, nullable=False),
    Column("supplier_snapshot", JSONB, nullable=False),
    Column("item_description", Text, nullable=False),
    Column("delivery_location", Text, nullable=False),
    Column("reward", Integer, nullable=False),
    Column("state", Text, nullable=False),
    Column("reservation_id", UUID, nullable=False),
    Column("acceptance_deadline", DateTime(timezone=True), nullable=False),
    Column("delivery_deadline", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

history = Table(
    "order_history",
    metadata,
    Column("order_id", UUID, ForeignKey("order_service.orders.id"), primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("previous_state", Text),
    Column("new_state", Text, nullable=False),
    Column("actor_id", UUID, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)
