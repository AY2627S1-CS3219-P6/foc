"""Self-owned User Service identity endpoints."""

# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.authentication import REFRESH_COOKIE_NAME
from app.api.schemas import AccountDeletionRequest, CurrentUserResponse, ProfileUpdateRequest
from app.auth.dependencies import AuthenticatedPrincipal, require_self_access
from app.db import get_db_session
from app.profile.service import ProfileService

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_self_access)],
) -> CurrentUserResponse:
    """Return the safe profile of the server-validated current caller only."""

    user = principal.user
    return CurrentUserResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        system_role=user.system_role,
        account_status=user.account_status,
    )


@router.patch("/me", response_model=CurrentUserResponse)
async def update_current_user(
    body: ProfileUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_self_access)],
) -> CurrentUserResponse:
    """Update the authenticated caller's allow-listed profile preferences only."""

    user = await ProfileService().update_profile(session, user_id=principal.user.id, changes=body)
    return CurrentUserResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        system_role=user.system_role,
        account_status=user.account_status,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    body: AccountDeletionRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_self_access)],
) -> None:
    """Anonymize this caller's profile and remove its authentication material."""

    await ProfileService().delete_account(
        session,
        user_id=principal.user.id,
        current_password=body.current_password,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/v1/auth",
        httponly=True,
        secure=request.app.state.settings.environment == "production",
        samesite="lax",
    )
