import secrets
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PostgresDsn, SecretStr, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogSettings(BaseModel):
    """Logging configuration."""

    LEVEL: LogLevel = "INFO"
    FILE_PATH: str | None = None
    DISABLE_COLORS: bool = False


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    SERVER: str = "localhost"
    PORT: Annotated[int, Field(ge=1, le=65535)] = 5432
    USER: str = "postgres"
    PASSWORD: Annotated[SecretStr, Field(min_length=16)] = SecretStr("")
    DB: str = ""


class SuperUserSettings(BaseModel):
    """Superuser configuration."""

    NAME: str = "admin"
    EMAIL: str = "admin@example.com"
    PASSWORD: Annotated[SecretStr, Field(min_length=16)] = SecretStr("admin")


class JWTSettings(BaseModel):
    """JWT authentication configuration."""

    SECRET_KEY: Annotated[SecretStr, Field(min_length=32)] = SecretStr(
        secrets.token_urlsafe(32)
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


class Settings(BaseSettings):
    """Application configuration settings."""

    VERSION: str = "1.0.0"
    API_PATH: str = "/api/v1"
    APPLICATION_NAME: str = "FastAPI Supabase Template"
    CORS_ORIGINS: list[str] = ["*"]

    LOG: LogSettings = LogSettings()
    DATABASE: DatabaseSettings = DatabaseSettings()
    SUPER_USER: SuperUserSettings = SuperUserSettings()
    JWT: JWTSettings = JWTSettings()

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> PostgresDsn:
        """Returns the database connection URL."""
        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+asyncpg",
                username=self.DATABASE.USER,
                password=self.DATABASE.PASSWORD.get_secret_value(),
                host=self.DATABASE.SERVER,
                port=self.DATABASE.PORT,
                path=self.DATABASE.DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> PostgresDsn:
        """Get the sync database URL for Alembic."""
        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.DATABASE.USER,
                password=self.DATABASE.PASSWORD.get_secret_value(),
                host=self.DATABASE.SERVER,
                port=self.DATABASE.PORT,
                path=self.DATABASE.DB,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
