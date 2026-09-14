from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Event Registration API"
    environment: str = "development"
    sse_poll_interval_seconds: float = Field(default=1.0, gt=0)
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=1025, gt=0, le=65535)
    smtp_from: str = "events@example.local"
    notification_poll_interval_seconds: float = Field(default=2.0, gt=0)
    notification_claim_timeout_seconds: float = Field(default=60.0, gt=0)
    notification_batch_size: int = Field(default=20, gt=0, le=1000)
    reminder_lead_hours: float = Field(default=24.0, gt=0)
    database_url: str = (
        "postgresql+psycopg://event_registration:event_registration@localhost:5432/"
        "event_registration"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
