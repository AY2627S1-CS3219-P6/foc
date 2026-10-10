"""Dedicated, private User Service contracts for Chat Service."""

# ruff: noqa: B008

from __future__ import annotations

from collections.abc import AsyncIterator
from hmac import compare_digest
from typing import Annotated

from asyncpg import PostgresError
from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat_schemas import ChatUserSearchQuery, ChatUserSearchResponse
from app.api.errors import ApiError
from app.auth.dependencies import get_current_principal, require_self_access
from app.auth.service import AuthenticatedPrincipal
from app.chat.service import search_users
from app.core.config import Settings
from app.db import DatabaseUnavailableError, get_db_session

CHAT_INTERFACE_PATHS = {"/v1/internal/chat/users", "/v1/internal/chat/participants"}


def require_chat_service_identity(
    request: Request,
    supplied_secret: Annotated[str | None, Header(alias="X-FoC-Service-Secret")] = None,
) -> None:
    """Fail closed without accepting the Supplier or legacy internal identity."""

    settings: Settings = request.app.state.settings
    configured = settings.chat_service_shared_secret
    if (
        configured is None
        or supplied_secret is None
        or not compare_digest(
            supplied_secret.encode("utf-8"), configured.get_secret_value().encode("utf-8")
        )
    ):
        raise ApiError(401, "INVALID_SERVICE_IDENTITY", "Service authentication is required.")


router = APIRouter(
    prefix="/v1/internal/chat",
    tags=["internal-chat"],
    dependencies=[Depends(require_chat_service_identity)],
)


async def get_chat_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Translate database outages for both caller checks and identity queries."""

    try:
        async for session in get_db_session(request):
            yield session
    except (SQLAlchemyError, PostgresError, OSError, TimeoutError) as error:
        raise DatabaseUnavailableError("Database is unavailable.") from error


async def require_chat_caller(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_chat_db_session)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedPrincipal:
    """Reuse current session and inherited self-access rules for every role."""

    principal = await get_current_principal(request, session, authorization)
    return await require_self_access(principal)


@router.get("/users", response_model=ChatUserSearchResponse)
async def chat_user_search(
    query: Annotated[ChatUserSearchQuery, Query()],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_chat_caller)],
    session: Annotated[AsyncSession, Depends(get_chat_db_session)],
) -> ChatUserSearchResponse:
    return await search_users(session, query=query, caller_id=principal.user.id)
