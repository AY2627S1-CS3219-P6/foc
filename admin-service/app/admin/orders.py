"""Order Service read used to confirm that a disputed errand exists (N2F3.2.2)."""

import asyncio
from uuid import UUID

import httpx

from app.admin.errors import ApiError, unavailable
from app.core.config import Settings


class OrderDirectory:
    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self.settings = settings
        self.http = http

    async def exists(self, order_id: UUID, token: str) -> bool:
        """Forward the administrator's own token; Order re-checks the role itself."""
        response = await self._get(f"/v1/admin/orders/{order_id}", token)
        if response.status_code == 404:
            return False
        return True

    async def participation(self, order_id: UUID, token: str, user_id: UUID):
        """The caller's role and the errand state from Order's participant view, or None.

        Order shows requester and courier identities only to the errand's participants.
        """
        response = await self._get(f"/v1/orders/{order_id}", token)
        if response.status_code == 404:
            return None
        try:
            body = response.json()
            state = body["state"]
            requester, courier = body.get("requesterId"), body.get("courierId")
        except (ValueError, KeyError, TypeError, AttributeError):
            raise unavailable("ORDER_UNAVAILABLE") from None
        if requester == str(user_id):
            return "REQUESTER", state
        if courier == str(user_id):
            return "COURIER", state
        return None

    async def _get(self, path: str, token: str) -> httpx.Response:
        base = self.settings.order_service_base_url
        if not base:
            raise unavailable("ORDER_UNAVAILABLE")
        try:
            async with asyncio.timeout(self.settings.dependency_timeout_seconds):
                response = await self.http.get(
                    base + path,
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                    timeout=self.settings.dependency_timeout_seconds,
                )
        except (httpx.HTTPError, TimeoutError):
            raise unavailable("ORDER_UNAVAILABLE") from None
        if response.status_code in (200, 404):
            return response
        if response.status_code == 401:
            raise ApiError(401, "UNAUTHENTICATED", "A current active session is required.")
        if response.status_code == 403:
            raise ApiError(403, "FORBIDDEN", "Administrator access is required.")
        raise unavailable("ORDER_UNAVAILABLE")
