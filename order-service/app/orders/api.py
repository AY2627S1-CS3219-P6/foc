"""Authenticated create/read endpoints; Order owns relationship authorization."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.orders.errors import ApiError, not_found
from app.orders.schemas import (
    AdminQuery,
    CreateOrder,
    CreationResponse,
    HistoryEntry,
    OpenQuery,
    OrderAssessment,
    OrderParticipant,
    OwnQuery,
    Page,
    PageQuery,
)
from app.orders.service import CreationService, operation_view, project_order, visible_order

router = APIRouter(prefix="/v1", tags=["Orders"])


async def authenticate(request: Request, authorization: Annotated[str | None, Header()] = None):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "UNAUTHENTICATED", "A bearer token is required.")
    principal = await request.app.state.clients.identity(token.strip())
    return principal, token.strip()


Auth = Annotated[tuple, Depends(authenticate)]


def page_result(items, total, query):
    return {"items": items, "total": total, "page": query.page, "pageSize": query.page_size}


@router.post(
    "/orders",
    status_code=201,
    response_model=OrderParticipant,
    responses={
        200: {"model": OrderParticipant, "description": "Successful idempotent replay"},
        202: {"model": CreationResponse, "description": "Creation operation, not an OPEN order"},
    },
)
async def create_order(
    request: Request,
    body: CreateOrder,
    auth: Auth,
    idempotency_key: Annotated[str | None, Header()] = None,
):
    principal, token = auth
    service = CreationService(request.app.state.repository, request.app.state.clients)
    status, result = await service.create(principal.user_id, token, idempotency_key, body)
    headers = {"Location": result["statusUrl"], "Retry-After": "5"} if status == 202 else {}
    model = CreationResponse if status == 202 else OrderParticipant
    response = model.model_validate(result)
    return JSONResponse(status_code=status, content=jsonable_encoder(response), headers=headers)


@router.get("/order-creations/{operation_id}", response_model=CreationResponse)
async def creation_status(operation_id: UUID, request: Request, auth: Auth):
    operation = await request.app.state.repository.operation(operation_id)
    if operation is None or operation["requester_id"] != auth[0].user_id:
        raise not_found()
    return operation_view(operation)


@router.get("/orders", response_model=Page[OrderAssessment])
async def open_orders(request: Request, auth: Auth, query: Annotated[OpenQuery, Query()]):
    rows, total = await request.app.state.repository.list_orders(query, available=True)
    return page_result([project_order(row) for row in rows], total, query)


@router.get("/orders/mine", response_model=Page[OrderParticipant])
async def own_orders(request: Request, auth: Auth, query: Annotated[OwnQuery, Query()]):
    rows, total = await request.app.state.repository.list_orders(
        query,
        **{query.relationship: auth[0].user_id},
    )
    return page_result([project_order(row, participant=True) for row in rows], total, query)


@router.get("/admin/orders", response_model=Page[OrderParticipant])
async def admin_orders(request: Request, auth: Auth, query: Annotated[AdminQuery, Query()]):
    if auth[0].system_role not in ("ADMIN", "SUPER_ADMIN"):
        raise ApiError(403, "FORBIDDEN", "Current administrator permission is required.")
    rows, total = await request.app.state.repository.list_orders(
        query, requester=query.requester_id
    )
    return page_result([project_order(row, participant=True) for row in rows], total, query)


@router.get("/orders/{order_id}", response_model=OrderParticipant | OrderAssessment)
async def order_detail(order_id: UUID, request: Request, auth: Auth):
    row, participant = await visible_order(request.app.state.repository, order_id, auth[0].user_id)
    return project_order(row, participant=participant)


@router.get("/orders/{order_id}/history", response_model=Page[HistoryEntry])
async def order_history(
    order_id: UUID,
    request: Request,
    auth: Auth,
    query: Annotated[PageQuery, Query()],
):
    await visible_order(
        request.app.state.repository, order_id, auth[0].user_id, participant_only=True
    )
    rows, total = await request.app.state.repository.order_history(order_id, query)
    return page_result(
        [
            {
                "sequence": row["sequence"],
                "previousState": row["previous_state"],
                "newState": row["new_state"],
                "actorId": row["actor_id"],
                "actorType": row["actor_type"],
                "occurredAt": row["occurred_at"],
            }
            for row in rows
        ],
        total,
        query,
    )
