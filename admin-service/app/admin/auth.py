"""Every dashboard request re-checks the caller's current session and role (N2NFR1.1-1.3)."""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.admin.errors import ApiError
from app.admin.schemas import Principal


async def authenticate(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> Principal:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "UNAUTHENTICATED", "A bearer token is required.")
    return await request.app.state.identity.identity(token.strip())


async def require_admin(principal: Annotated[Principal, Depends(authenticate)]) -> Principal:
    # N2F1.1.1: the role comes from User's current state, never from the token's claims.
    if principal.system_role not in ("ADMIN", "SUPER_ADMIN"):
        raise ApiError(403, "FORBIDDEN", "Administrator access is required.")
    return principal


Admin = Annotated[Principal, Depends(require_admin)]
