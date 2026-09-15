from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Event Registration API"
    environment: str = "development"
    sse_poll_interval_seconds: float = Field(default=1.0, gt=0)
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=1025, gt=0, le=65535)
    smtp_from: str = "events@example.local"
    # Optional, for pointing the worker at a real provider; Mailpit needs neither.
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    frontend_base_url: str = "http://localhost:5173"
    # Shared secret for organizer/staff routes; unset means open (local development).
    organizer_key: str | None = None

    @field_validator("organizer_key")
    @classmethod
    def organizer_key_must_be_header_safe(cls, value: str | None) -> str | None:
        # The key travels in an HTTP header, which cannot carry non-ASCII text; a browser refuses
        # to send such a header at all. Fail at startup instead of at the first request.
        if value is None:
            return None
        if not value or not all(0x21 <= ord(character) <= 0x7E for character in value):
            raise ValueError(
                "ORGANIZER_KEY must contain only printable ASCII characters without spaces"
            )
        return value

    notification_poll_interval_seconds: float = Field(default=2.0, gt=0)
    notification_claim_timeout_seconds: float = Field(default=60.0, gt=0)
    notification_batch_size: int = Field(default=20, gt=0, le=1000)
    notification_max_attempts: int = Field(default=5, gt=0)
    notification_retry_base_seconds: float = Field(default=5.0, gt=0)
    notification_retry_max_seconds: float = Field(default=300.0, gt=0)
    reminder_lead_hours: float = Field(default=24.0, gt=0)
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = (
        "postgresql+psycopg://event_registration:event_registration@localhost:5432/"
        "event_registration"
    )
    database_pool_size: int = Field(default=5, gt=0)
    database_max_overflow: int = Field(default=10, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
