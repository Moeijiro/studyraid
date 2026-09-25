"""Runtime configuration, read from environment variables (and backend/.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-only-secret-change-me-dev-only-secret-change-me"  # noqa: S105 - refused in production


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+aiosqlite:///./studyraid.db"
    sql_echo: bool = False

    # Auth
    secret_key: str = _DEV_SECRET
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    cookie_secure: bool = False
    allow_registration: bool = True

    # Browsers reach the API through the Next.js proxy; the WebSocket connects
    # directly, so its Origin header is checked against this list.
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Background scheduler (reminders, expiry, challenge settlement).
    worker_enabled: bool = True
    worker_interval_seconds: float = Field(default=60, ge=1)

    # Demo mode exposes the demo credentials on /api/system/info.
    demo_mode: bool = True

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> "Settings":
        if self.environment == "production":
            if self.secret_key == _DEV_SECRET or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a random value of at least 32 characters in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be false in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
