"""Async PostgreSQL connectivity and request-session dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.logging import logger

_ASYNC_POSTGRESQL_SCHEME = "postgresql+asyncpg://"
_DATABASE_CONNECT_TIMEOUT_SECONDS = 5


class DatabaseUnavailableError(RuntimeError):
    """Raised when a request needs a database session that is not configured."""


def async_database_url(database_url: str) -> str:
    """Use asyncpg for ordinary PostgreSQL URLs supplied by deployment config."""

    if database_url.startswith("postgres://"):
        return _ASYNC_POSTGRESQL_SCHEME + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return _ASYNC_POSTGRESQL_SCHEME + database_url.removeprefix("postgresql://")
    return database_url


class Database:
    """Own the SQLAlchemy engine without performing schema changes."""

    def __init__(self, database_url: str | None) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        if database_url:
            self._engine = create_async_engine(
                async_database_url(database_url),
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                connect_args={"timeout": _DATABASE_CONNECT_TIMEOUT_SECONDS},
            )
            self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def configured(self) -> bool:
        return self._engine is not None

    async def ping(self) -> bool:
        """Check PostgreSQL availability with a read-only query."""

        if self._engine is None:
            logger.warning(
                "database is not configured",
                extra={
                    "event": "database_connectivity_check",
                    "context": {"databaseConfigured": False, "ready": False},
                },
            )
            return False
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            logger.warning(
                "database is not ready",
                extra={
                    "event": "database_connectivity_check",
                    "context": {
                        "databaseConfigured": True,
                        "errorType": type(error).__name__,
                        "ready": False,
                    },
                },
            )
            return False

        logger.info(
            "database is ready",
            extra={
                "event": "database_connectivity_check",
                "context": {"databaseConfigured": True, "ready": True},
            },
        )
        return True

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a transaction-capable session for future request handlers."""

        if self._session_factory is None:
            raise DatabaseUnavailableError("Database is not configured.")
        async with self._session_factory() as session:
            yield session

    async def dispose(self) -> None:
        """Release connection-pool resources on application shutdown."""

        if self._engine is not None:
            await self._engine.dispose()


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for endpoints that need User Service persistence."""

    database: Database = request.app.state.database
    async for session in database.session():
        yield session
