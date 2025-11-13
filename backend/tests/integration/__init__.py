"""Integration test configuration."""

from pydantic import SecretStr

from app.config import DatabaseSettings, LogSettings, Settings


class IntegrationSettings(Settings):
    """Test-specific settings with database and logging overrides."""

    DATABASE: DatabaseSettings = DatabaseSettings(
        SERVER="localhost",
        PORT=5432,
        USER="test_user",
        PASSWORD=SecretStr("test_password"),
        DB="fastapi_test",
    )
    LOG: LogSettings = LogSettings(
        LEVEL="WARNING",
        DISABLE_COLORS=True,
    )
