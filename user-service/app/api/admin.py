"""Super Admin-only system-role lifecycle endpoints."""

# ruff: noqa: B008

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.accounts import AdminAccountService
from app.admin.lifecycle import AdminLifecycleService
from app.api.schemas import (
    AdminUserLookupRequest,
    AdminUserLookupResponse,
    SystemRoleUpdateRequest,
    SystemRoleUpdateResponse,
)
from app.auth.dependencies import AuthenticatedPrincipal, require_admin, require_super_admin
from app.core.correlation import get_correlation_id
from app.db import get_db_session

router = APIRouter(prefix="/v1/admin", tags=["administration"])


@router.get("/users", response_model=AdminUserLookupResponse)
async def find_user_account(
    criteria: Annotated[AdminUserLookupRequest, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedPrincipal, Depends(require_admin)],
) -> AdminUserLookupResponse:
    """Return only the requested account's safe administrative profile fields."""

    user = await AdminAccountService().find_by_identity(
        session,
        username=criteria.username,
        email=criteria.email,
    )
    return AdminUserLookupResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        account_status=user.account_status,
        system_role=user.system_role,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}/system-role", response_model=SystemRoleUpdateResponse)
async def update_system_role(
    user_id: UUID,
    body: SystemRoleUpdateRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_super_admin)],
) -> SystemRoleUpdateResponse:
    """Change another active identity's role with server-side authorization only."""

    user = await AdminLifecycleService().change_system_role(
        session,
        actor_id=principal.user.id,
        target_user_id=user_id,
        requested_role=body.system_role,
        correlation_id=get_correlation_id(request),
    )
    return SystemRoleUpdateResponse(
        user_id=user.id,
        system_role=user.system_role,
        role_version=user.role_version,
    )
