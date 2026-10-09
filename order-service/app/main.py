"""Order application factory and operational endpoints; no business APIs in F0."""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.db import Database

_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    service_settings = settings if settings is not None else get_settings()
    database_url = service_settings.database_url
    service_database = database if database is not None else Database(
        database_url.get_secret_value() if database_url else None
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Defer database connections so an outage cannot prevent liveness from starting.
        try:
            yield
        finally:
            await service_database.dispose()

    app = FastAPI(
        title="FoC Order Service",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if service_settings.environment == "production" else "/docs",
        redoc_url=None,
    )
    app.state.database = service_database

    @app.middleware("http")
    async def correlate_request(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = (
            supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else uuid4().hex
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    def unavailable(request: Request) -> JSONResponse:
        return JSONResponse(status_code=503, content={"error": {
            "code": "SERVICE_NOT_READY",
            "message": "The Order database is not ready.",
            "correlationId": request.state.correlation_id,
            "fieldErrors": [],
        }})

    @app.get("/health/live", tags=["Operations"])
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["Operations"], response_model=None)
    async def ready(request: Request) -> dict[str, str] | JSONResponse:
        if not await service_database.ping():
            return unavailable(request)
        return {"status": "ready"}

    return app


app = create_app()
