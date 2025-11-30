from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BaseModel, Field, PostgresDsn, SecretStr, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.auth.config import AuthSettings

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
Environment = Literal["development", "staging", "production"]


class LogSettings(BaseModel):
    """Logging configuration."""

    level: LogLevel = "INFO"
    file_path: str | None = None
    disable_colors: bool = False


class DatabaseSettings(BaseModel):
    """Database connection configuration."""

    server: str = "localhost"
    port: Annotated[int, Field(ge=1, le=65535)] = 5432
    user: str = "postgres"
    password: SecretStr = SecretStr("your-secure-password")
    db: str = "app"


class SuperUserSettings(BaseModel):
    """Superuser configuration."""

    name: str = "admin"
    email: str = "admin@example.com"
    password: SecretStr = SecretStr("admin")


class AuthFeatureSettings(BaseModel):
    """Authentication feature toggles.

    Controls which authentication features are enabled at runtime.
    When auth is disabled, no auth routes or user management endpoints are registered.
    Database tables are always created regardless of these settings.
    """

    enabled: bool = Field(
        default=True,
        description="Master switch for authentication. When False, no auth or user routes registered.",
    )
    jwt_enabled: bool = Field(
        default=True,
        description="Enable JWT authentication provider.",
    )
    api_key_enabled: bool = Field(
        default=True,
        description="Enable API Key authentication provider.",
    )


class FeatureSettings(BaseModel):
    """Application feature toggles."""

    auth: AuthFeatureSettings = Field(default_factory=AuthFeatureSettings)


class Settings(BaseSettings):
    """Application configuration settings."""

    environment: Environment = "development"
    version: str = "1.0.0"
    api_path: str = "/api/v1"
    application_name: str = "FastAPI Template"
    cors_origins: list[str] = ["*"]

    log: LogSettings = Field(default_factory=LogSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    super_user: SuperUserSettings = Field(default_factory=SuperUserSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    features: FeatureSettings = Field(default_factory=FeatureSettings)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> PostgresDsn:
        """Build the async database connection URL.

        Returns:
            PostgresDsn: Async database URL using asyncpg driver.
        """
        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+asyncpg",
                username=self.database.user,
                password=self.database.password.get_secret_value(),
                host=self.database.server,
                port=self.database.port,
                path=self.database.db,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> PostgresDsn:
        """Build the sync database connection URL for Alembic migrations.

        Returns:
            PostgresDsn: Sync database URL using psycopg driver.
        """
        return PostgresDsn(
            MultiHostUrl.build(
                scheme="postgresql+psycopg",
                username=self.database.user,
                password=self.database.password.get_secret_value(),
                host=self.database.server,
                port=self.database.port,
                path=self.database.db,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
