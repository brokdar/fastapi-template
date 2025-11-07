from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Application configuration settings."""

    VERSION: str = "1.0.0"
    API_PATH: str = "/api/v1"
    APPLICATION_NAME: str = "FastAPI Supabase Template"
    CORS_ORIGINS: list[str] = ["*"]

    LOG_LEVEL: LogLevel = "INFO"
    LOG_FILE_PATH: str | None = None
    LOG_DISABLE_COLORS: bool = False

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
