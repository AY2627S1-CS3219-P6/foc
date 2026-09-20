"""Safe application errors shared by User Service route handlers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldError:
    """One safe, field-specific validation or conflict message."""

    field: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass
class ApiError(Exception):
    """An intentional public error that cannot include request secrets."""

    status_code: int
    code: str
    message: str
    field_errors: list[FieldError] = field(default_factory=list)
