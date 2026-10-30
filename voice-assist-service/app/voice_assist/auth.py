"""Every route re-checks the caller's current session with User (N3NFR3.1)."""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.voice_assist.errors import ApiError
from app.voice_assist.schemas import Principal


async def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "UNAUTHENTICATED", "A bearer token is required.")
    return token.strip()


BearerToken = Annotated[str, Depends(bearer_token)]


async def authenticate(request: Request, token: BearerToken) -> Principal:
    return await request.app.state.identity.identity(token)


Requester = Annotated[Principal, Depends(authenticate)]
