"""Safe request-duration instrumentation used by the D2 timing evidence."""

from __future__ import annotations

from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Emit redacted per-request duration data without retaining request bodies."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started_at = perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_milliseconds = round((perf_counter() - started_at) * 1_000, 3)
            if response is not None:
                response.headers["X-Response-Time-Ms"] = str(elapsed_milliseconds)
            logger.info(
                "request completed",
                extra={
                    "event": "http_request_completed",
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "statusCode": response.status_code if response is not None else 500,
                        "durationMs": elapsed_milliseconds,
                    },
                },
            )
