"""Dispute workflow and dashboard audit log (N2F3). Decisions never change errands or credits."""

import logging
from typing import Annotated
from uuid import UUID

from asyncpg import PostgresError
from fastapi import APIRouter, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.admin.auth import Admin, BearerToken
from app.admin.disputes import DisputeNotFound, OrderNotFound, request_fingerprint
from app.admin.errors import ApiError
from app.admin.schemas import (
    AuditEntry,
    AuditQuery,
    CreateDispute,
    DisputeQuery,
    DisputeSummary,
    DisputeView,
    HistoryEntry,
    Page,
    Transition,
)
from app.db import DatabaseUnavailableError

logger = logging.getLogger("foc.admin.disputes")
router = APIRouter(prefix="/v1/admin", tags=["Disputes"])


def parse_key(value: str | None) -> UUID:
    try:
        return UUID(value or "")
    except ValueError:
        raise ApiError(
            422, "IDEMPOTENCY_KEY_REQUIRED", "Send a UUID Idempotency-Key header."
        ) from None


async def record_rejection(request: Request, actor: UUID, action, target_type, target_id, error):
    # N2F3.6: rejected attempts are audited after their own transaction rolled back.
    try:
        await request.app.state.disputes.record_rejection(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            correlation_id=request.state.correlation_id,
            error_code=error.code,
        )
    except (SQLAlchemyError, PostgresError, DatabaseUnavailableError, OSError, TimeoutError):
        logger.warning("A rejected dispute action could not be audited")


def summary_fields(row) -> dict:
    return {
        "dispute_id": row["id"],
        "order_id": row["order_id"],
        "description": row["description"],
        "status": row["status"],
        "resolution_reason": row["resolution_reason"],
        "reporter_role": row.get("reporter_role"),
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "version": row["version"],
    }


async def load_dispute(request: Request, dispute_id: UUID) -> DisputeView:
    row, events = await request.app.state.disputes.dispute(dispute_id)
    if row is None:
        raise DisputeNotFound()
    return DisputeView(
        **summary_fields(row),
        evidence_refs=list(row["evidence_refs"]),
        history=[
            HistoryEntry(
                sequence=event["sequence"],
                from_status=event["from_status"],
                to_status=event["to_status"],
                actor_id=event["actor_id"],
                reason=event["reason"],
                occurred_at=event["occurred_at"],
            )
            for event in events
        ],
    )


@router.post(
    "/disputes",
    status_code=201,
    response_model=DisputeView,
    responses={200: {"model": DisputeView, "description": "Replay of an identical request"}},
)
async def create_dispute(
    request: Request,
    body: CreateDispute,
    admin: Admin,
    token: BearerToken,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    key = parse_key(idempotency_key)
    try:
        if not await request.app.state.orders.exists(body.order_id, token):
            raise OrderNotFound()
        dispute_id, created = await request.app.state.disputes.create(
            order_id=body.order_id,
            description=body.description,
            evidence_refs=body.evidence_refs,
            actor=admin.user_id,
            key=key,
            fingerprint=request_fingerprint(body.order_id, body.description, body.evidence_refs),
            correlation_id=request.state.correlation_id,
        )
    except ApiError as error:
        await record_rejection(
            request, admin.user_id, "DISPUTE_CREATE", "ORDER", body.order_id, error
        )
        raise
    view = await load_dispute(request, dispute_id)
    return JSONResponse(status_code=201 if created else 200, content=jsonable_encoder(view))


@router.get("/disputes", response_model=Page[DisputeSummary])
async def list_disputes(request: Request, admin: Admin, query: Annotated[DisputeQuery, Query()]):
    rows, total = await request.app.state.disputes.disputes_page(
        status=query.status, order_id=query.order_id, page=query.page, page_size=query.page_size
    )
    return Page[DisputeSummary](
        items=[DisputeSummary(**summary_fields(row)) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


@router.get("/disputes/{dispute_id}", response_model=DisputeView)
async def get_dispute(dispute_id: UUID, request: Request, admin: Admin):
    return await load_dispute(request, dispute_id)


@router.post("/disputes/{dispute_id}/transitions", response_model=DisputeView)
async def change_status(dispute_id: UUID, request: Request, body: Transition, admin: Admin):
    try:
        await request.app.state.disputes.transition(
            dispute_id,
            to_status=body.to_status,
            reason=body.reason,
            expected_version=body.expected_version,
            actor=admin.user_id,
            correlation_id=request.state.correlation_id,
        )
    except ApiError as error:
        await record_rejection(
            request, admin.user_id, "DISPUTE_TRANSITION", "DISPUTE", dispute_id, error
        )
        raise
    return await load_dispute(request, dispute_id)


@router.get("/audit-log", response_model=Page[AuditEntry])
async def list_audit_log(request: Request, admin: Admin, query: Annotated[AuditQuery, Query()]):
    rows, total = await request.app.state.disputes.audit_page(
        actor_id=query.actor_id,
        target_id=query.target_id,
        outcome=query.outcome,
        page=query.page,
        page_size=query.page_size,
    )
    return Page[AuditEntry](
        items=[
            AuditEntry(
                audit_id=row["id"],
                actor_id=row["actor_id"],
                action=row["action"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                outcome=row["outcome"],
                error_code=row["error_code"],
                correlation_id=row["correlation_id"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        ],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )
