"""Integration test configuration."""

from pydantic import SecretStr

from app.config import (
    DatabaseSettings,
    LogSettings,
    Settings,
)
from app.core.auth.config import AuthSettings
from app.core.auth.providers.api_key.config import APIKeySettings


class IntegrationSettings(Settings):
    """Test-specific settings with database and logging overrides."""

    database: DatabaseSettings = DatabaseSettings(
        server="localhost",
        port=5432,
        user="test_user",
        password=SecretStr("test_password"),
        db="fastapi_test",
    )
    log: LogSettings = LogSettings(
        level="WARNING",
        disable_colors=True,
    )
    auth: AuthSettings = AuthSettings(
        api_key=APIKeySettings(enabled=True),
    )
