"""Typed, local-file-aware service configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuration kept outside application source and container images."""

    model_config = SettingsConfigDict(
        env_file=SERVICE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "foc-user-service"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url_is_unconfigured(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance for the running process."""

    return Settings()
