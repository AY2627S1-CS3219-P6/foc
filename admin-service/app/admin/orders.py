"""Order Service calls: errand checks (N2F3.2.2) and dispute errand outcomes (N2F3.7)."""

import asyncio
from uuid import UUID

import httpx

from app.admin.disputes import ErrandChanged, OrderNotFound
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

    async def decide(
        self, order_id: UUID, outcome: str, dispute_id: UUID, reason: str, token: str
    ) -> None:
        """Fail or complete the errand for this dispute; Order re-checks the role and state.

        Order treats a repeat of the same decision for the same dispute as success, so a retry
        after an ambiguous failure is safe.
        """
        action = "fail" if outcome == "FAILED" else "complete"
        body = {"disputeId": str(dispute_id)}
        if action == "fail":
            body["reason"] = reason
        response = await self._send(
            "POST", f"/v1/admin/orders/{order_id}/{action}", token, json=body
        )
        if response.status_code == 404:
            raise OrderNotFound()

    async def _get(self, path: str, token: str) -> httpx.Response:
        return await self._send("GET", path, token)

    async def _send(self, method: str, path: str, token: str, json=None) -> httpx.Response:
        base = self.settings.order_service_base_url
        if not base:
            raise unavailable("ORDER_UNAVAILABLE")
        try:
            async with asyncio.timeout(self.settings.dependency_timeout_seconds):
                response = await self.http.request(
                    method,
                    base + path,
                    headers={"Authorization": f"Bearer {token}"},
                    json=json,
                    follow_redirects=False,
                    timeout=self.settings.dependency_timeout_seconds,
                )
        except (httpx.HTTPError, TimeoutError):
            raise unavailable("ORDER_UNAVAILABLE") from None
        if response.status_code == 409 and method == "POST":
            raise ErrandChanged()
        if response.status_code in (200, 404):
            return response
        if response.status_code == 401:
            raise ApiError(401, "UNAUTHENTICATED", "A current active session is required.")
        if response.status_code == 403:
            raise ApiError(403, "FORBIDDEN", "Administrator access is required.")
        raise unavailable("ORDER_UNAVAILABLE")
