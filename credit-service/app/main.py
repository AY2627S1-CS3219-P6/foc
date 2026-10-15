"""Credit application factory, operational endpoints and versioned business API."""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from asyncpg import PostgresError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings, get_settings
from app.credits.errors import ApiError, CreditError
from app.db import Database, DatabaseUnavailableError

_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def _envelope(request: Request, status: int, code: str, message: str, field_errors=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlationId": request.state.correlation_id,
                "fieldErrors": field_errors or [],
            }
        },
    )


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    *,
    ledger=None,
    identity=None,
) -> FastAPI:
    service_settings = settings if settings is not None else get_settings()
    database_url = service_settings.database_url
    service_database = (
        database
        if database is not None
        else Database(database_url.get_secret_value() if database_url else None)
    )
    http = httpx.AsyncClient(trust_env=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Defer database connections so an outage cannot prevent liveness from starting.
        try:
            yield
        finally:
            await http.aclose()
            await service_database.dispose()

    app = FastAPI(
        title="FoC Credit Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if service_settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.settings = service_settings
    app.state.database = service_database
    app.state.ledger = ledger
    app.state.identity = identity

    @app.exception_handler(ApiError)
    async def domain_error(request: Request, error: ApiError):
        return _envelope(request, error.status, error.code, error.message)

    @app.exception_handler(CreditError)
    async def credit_rejected(request: Request, error: CreditError):
        return _envelope(request, 409, error.code, "The credit operation was rejected.")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # Never serialize Pydantic input/context: they may contain confidential payloads.
        return _envelope(
            request,
            422,
            "VALIDATION_ERROR",
            "Check the request fields.",
            [
                {
                    "field": ".".join(str(part) for part in item["loc"]),
                    "message": "Invalid or unsupported field.",
                }
                for item in error.errors()
            ],
        )

    async def database_error(request: Request, error: Exception):
        return _envelope(
            request, 503, "DATABASE_UNAVAILABLE", "Credit storage is unavailable. Retry safely."
        )

    for error_type in (
        SQLAlchemyError,
        PostgresError,
        DatabaseUnavailableError,
        OSError,
        TimeoutError,
    ):
        app.add_exception_handler(error_type, database_error)

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = (
            supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else uuid4().hex
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @app.get("/health/live", tags=["Operations"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["Operations"], response_model=None)
    async def ready(request: Request) -> dict[str, str] | JSONResponse:
        if not await service_database.ping():
            return _envelope(
                request, 503, "SERVICE_NOT_READY", "The Credit database is not ready."
            )
        return {"status": "ready"}

    return app


app = create_app()
