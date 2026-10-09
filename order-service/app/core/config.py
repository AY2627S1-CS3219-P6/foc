"""Typed configuration; no credentials are embedded in the application."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    user_service_base_url: str | None = None
    supplier_service_base_url: str | None = None
    credit_service_base_url: str | None = None
    credit_service_secret: SecretStr | None = None
    dependency_timeout_seconds: float = Field(default=2, gt=0, le=10)
    recovery_interval_seconds: float = Field(default=5, gt=0, le=60)
    recovery_batch_size: int = Field(default=50, ge=1, le=100)

    @field_validator(
        "user_service_base_url", "supplier_service_base_url", "credit_service_base_url"
    )
    @classmethod
    def service_origin(cls, value):
        if not value or not value.strip():
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Service URLs must be HTTP(S) origins without credentials or paths")
        return value.rstrip("/")

    @field_validator("credit_service_secret", mode="before")
    @classmethod
    def blank_credit_secret(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("database_url", mode="before")
    @classmethod
    def blank_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
