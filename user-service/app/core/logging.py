"""JSON logging that prevents structured context from exposing credentials."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.core.correlation import current_correlation_id

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "database_url",
    "otp",
    "password",
    "private_key",
    "refresh",
    "secret",
    "token",
)
_REDACTED = "[REDACTED]"


def is_sensitive_key(key: object) -> bool:
    """Identify data keys that must never reach a log sink."""

    normalized = str(key).casefold()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_context(value: Any, key: object | None = None) -> Any:
    """Recursively remove secrets from structured logging context."""

    if key is not None and is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_context(item_value, item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [redact_context(item) for item in value]
    return value


class RedactingFilter(logging.Filter):
    """Ensure explicitly supplied logging context is redacted before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, "context"):
            record.context = redact_context(record.context)
        for key in tuple(record.__dict__):
            if is_sensitive_key(key):
                record.__dict__[key] = _REDACTED
        return True


class JsonFormatter(logging.Formatter):
    """Write a compact structured log entry with correlation context."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlationId": getattr(record, "correlation_id", current_correlation_id.get()),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        if hasattr(record, "context"):
            payload["context"] = redact_context(record.context)
        if record.exc_info:
            payload["exceptionType"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str) -> None:
    """Configure only this service's logger to avoid changing host application logs."""

    logger = logging.getLogger("user_service")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False


logger = logging.getLogger("user_service")
