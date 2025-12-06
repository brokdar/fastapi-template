from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
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


class PostgresSettings(BaseModel):
    """PostgreSQL database connection configuration."""

    host: str = "localhost"
    port: Annotated[int, Field(ge=1, le=65535)] = 5432
    user: str = "postgres"
    password: SecretStr = SecretStr("your-secure-password")
    db: str = "app"


class SuperUserSettings(BaseModel):
    """Superuser configuration."""

    name: str = "admin"
    email: str = "admin@example.com"
    password: SecretStr = SecretStr("admin")


class RateLimitSettings(BaseModel):
    """Rate limiting configuration."""

    storage_uri: str | None = None


class Settings(BaseSettings):
    """Application configuration settings."""

    environment: Environment = "development"
    api_path: str = "/api/v1"
    application_name: str = "FastAPI Template"
    cors_origins: list[str] = ["*"]

    log: LogSettings = Field(default_factory=LogSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    super_user: SuperUserSettings = Field(default_factory=SuperUserSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def version(self) -> str:
        """Get application version from package metadata.

        Returns:
            str: Version string from Git tags via hatch-vcs.
        """
        try:
            return get_version("app")
        except PackageNotFoundError:
            return "0.0.0.dev0"

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
                username=self.postgres.user,
                password=self.postgres.password.get_secret_value(),
                host=self.postgres.host,
                port=self.postgres.port,
                path=self.postgres.db,
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
                username=self.postgres.user,
                password=self.postgres.password.get_secret_value(),
                host=self.postgres.host,
                port=self.postgres.port,
                path=self.postgres.db,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
