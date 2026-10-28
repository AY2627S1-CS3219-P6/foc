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
        base = self.settings.order_service_base_url
        if not base:
            raise unavailable("ORDER_UNAVAILABLE")
        try:
            async with asyncio.timeout(self.settings.dependency_timeout_seconds):
                response = await self.http.get(
                    f"{base}/v1/admin/orders/{order_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    follow_redirects=False,
                    timeout=self.settings.dependency_timeout_seconds,
                )
        except (httpx.HTTPError, TimeoutError):
            raise unavailable("ORDER_UNAVAILABLE") from None
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        if response.status_code == 401:
            raise ApiError(401, "UNAUTHENTICATED", "A current active session is required.")
        if response.status_code == 403:
            raise ApiError(403, "FORBIDDEN", "Administrator access is required.")
        raise unavailable("ORDER_UNAVAILABLE")
