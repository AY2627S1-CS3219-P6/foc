"""Self-owned User Service identity endpoints."""

# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas import CurrentUserResponse
from app.auth.dependencies import AuthenticatedPrincipal, get_current_principal

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
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
        active_participation_mode=user.active_participation_mode,
    )
