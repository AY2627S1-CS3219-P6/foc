"""Dedicated, private User Service contracts for Chat Service."""

# ruff: noqa: B008

from __future__ import annotations

from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.errors import ApiError
from app.core.config import Settings


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
