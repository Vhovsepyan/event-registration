from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Event Registration API"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://event_registration:event_registration@localhost:5432/"
        "event_registration"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
