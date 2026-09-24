"""Consistent, sanitized API errors."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields


def api_error_handler(_request: Request, error: ApiError) -> JSONResponse:
    body: dict[str, object] = {"code": error.code, "message": error.message}
    if error.fields is not None:
        body["fields"] = error.fields
    return JSONResponse(status_code=error.status_code, content={"error": body})


def validation_fields(errors: list[dict]) -> list[dict[str, str]]:
    return [
        {
            "field": ".".join(str(part) for part in item["loc"] if part != "body") or "body",
            "message": item["msg"],
        }
        for item in errors
    ]


def validation_error_handler(_request: Request, error: RequestValidationError) -> JSONResponse:
    return api_error_handler(
        _request,
        ApiError(422, "VALIDATION_ERROR", "Supplier data is invalid", validation_fields(error.errors())),
    )
