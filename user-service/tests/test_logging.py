import json
import logging

from app.core.correlation import current_correlation_id
from app.core.logging import JsonFormatter, RedactingFilter, redact_context


def test_structured_log_context_redacts_nested_secrets() -> None:
    context = {
        "request": {
            "password": "not-for-logs",
            "safeField": "safe",
        },
        "refreshToken": "not-for-logs",
    }

    assert redact_context(context) == {
        "request": {
            "password": "[REDACTED]",
            "safeField": "safe",
        },
        "refreshToken": "[REDACTED]",
    }


def test_structured_logs_include_request_correlation_id_without_secrets() -> None:
    record = logging.LogRecord(
        "user_service",
        logging.INFO,
        __file__,
        0,
        "registration request received",
        (),
        None,
    )
    record.context = {"password": "not-for-logs"}
    token = current_correlation_id.set("request-99")
    try:
        RedactingFilter().filter(record)
        output = JsonFormatter().format(record)
    finally:
        current_correlation_id.reset(token)

    assert json.loads(output)["correlationId"] == "request-99"
    assert "not-for-logs" not in output
