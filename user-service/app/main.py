"""FastAPI application factory and operations endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.correlation import CORRELATION_ID_HEADER, CorrelationIdMiddleware, get_correlation_id
from app.core.logging import configure_logging, logger
from app.db import Database


class ServiceNotReadyError(RuntimeError):
    """Raised when an operational dependency has not become available."""


def error_payload(code: str, message: str, correlation_id: str) -> dict[str, object]:
    """Use the contract's safe, consistent error envelope."""

    return {
        "error": {
            "code": code,
            "message": message,
            "correlationId": correlation_id,
            "fieldErrors": [],
        }
    }


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    """Build an independently testable application without running migrations."""

    service_settings = settings or get_settings()
    configure_logging(service_settings.log_level)
    service_database = database or Database(service_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "startup completed; database availability is reported by readiness",
            extra={"event": "startup_check", "context": {"databaseProbeDeferred": True}},
        )
        try:
            yield
        finally:
            await app.state.database.dispose()

    app = FastAPI(
        title="FoC User Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if service_settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.database = service_database
    app.add_middleware(CorrelationIdMiddleware)

    @app.exception_handler(ServiceNotReadyError)
    async def service_not_ready_handler(request: Request, _: ServiceNotReadyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_payload(
                "SERVICE_NOT_READY",
                "A required service dependency is not ready.",
                get_correlation_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
        """Keep error responses traceable without exposing implementation details."""

        correlation_id = get_correlation_id(request)
        logger.exception(
            "unhandled request error",
            extra={
                "correlation_id": correlation_id,
                "event": "unhandled_request_error",
                "context": {"errorType": type(error).__name__},
            },
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload(
                "INTERNAL_SERVER_ERROR",
                "An unexpected service error occurred.",
                correlation_id,
            ),
        )
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready(request: Request) -> dict[str, str]:
        if not await request.app.state.database.ping():
            raise ServiceNotReadyError()
        return {"status": "ready"}

    return app


app = create_app()
