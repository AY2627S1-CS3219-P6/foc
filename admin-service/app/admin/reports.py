"""Participant dispute reports (N2F3.2): requesters and couriers flag problems; admins decide.

These routes serve ordinary users. They confirm participation through Order's own participant
view and never expose administrator identities, history or audit records.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.admin.api import parse_key
from app.admin.auth import BearerToken, authenticate
from app.admin.disputes import (
    REPORTABLE_STATES,
    OrderNotFound,
    ReportNotAllowed,
    request_fingerprint,
)
from app.admin.schemas import Page, Principal, ReportProblem, ReportQuery, ReportView

router = APIRouter(prefix="/v1/disputes", tags=["Dispute reports"])
Caller = Annotated[Principal, Depends(authenticate)]


def report_view(row) -> ReportView:
    return ReportView(
        dispute_id=row["id"],
        order_id=row["order_id"],
        description=row["description"],
        status=row["status"],
        resolution_reason=row["resolution_reason"],
        reporter_role=row["reporter_role"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post(
    "",
    status_code=201,
    response_model=ReportView,
    responses={200: {"model": ReportView, "description": "Replay of an identical request"}},
)
async def report_problem(
    request: Request,
    body: ReportProblem,
    caller: Caller,
    token: BearerToken,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    key = parse_key(idempotency_key)
    # Non-participants get the same answer as for a missing errand, so nothing is disclosed.
    participation = await request.app.state.orders.participation(
        body.order_id, token, caller.user_id
    )
    if participation is None:
        raise OrderNotFound()
    role, state = participation
    if state not in REPORTABLE_STATES:
        raise ReportNotAllowed()
    dispute_id, created = await request.app.state.disputes.report(
        order_id=body.order_id,
        description=body.description,
        reporter=caller.user_id,
        role=role,
        key=key,
        fingerprint=request_fingerprint(body.order_id, body.description, []),
        correlation_id=request.state.correlation_id,
    )
    row, _ = await request.app.state.disputes.dispute(dispute_id)
    return JSONResponse(
        status_code=201 if created else 200, content=jsonable_encoder(report_view(row))
    )


@router.get("", response_model=Page[ReportView])
async def my_reports(request: Request, caller: Caller, query: Annotated[ReportQuery, Query()]):
    rows, total = await request.app.state.disputes.reports_for(
        caller.user_id, order_id=query.order_id, page=query.page, page_size=query.page_size
    )
    return Page[ReportView](
        items=[report_view(row) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )
