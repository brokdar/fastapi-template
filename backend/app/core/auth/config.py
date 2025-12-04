"""Authentication configuration settings.

This module assembles provider-specific settings into a unified AuthSettings
model. Each provider owns its configuration in its respective module.
"""

from pydantic import BaseModel, Field

from app.core.auth.providers.api_key.config import APIKeySettings
from app.core.auth.providers.jwt.config import JWTSettings


class AuthSettings(BaseModel):
    """Authentication configuration assembling all provider settings.

    Provider-specific settings are defined in their respective modules:
    - JWT: app.core.auth.providers.jwt.config.JWTSettings
    - API Key: app.core.auth.providers.api_key.config.APIKeySettings

    Environment variable examples (with AUTH__ prefix from parent):
        AUTH__ENABLED: Master switch for authentication
        AUTH__JWT__ENABLED: Enable JWT authentication provider
        AUTH__JWT__SECRET_KEY: JWT signing secret
        AUTH__JWT__ALGORITHM: JWT algorithm (default: HS256)
        AUTH__JWT__LOGIN_RATE_LIMIT: Rate limit for login (default: 5/minute)
        AUTH__JWT__REFRESH_RATE_LIMIT: Rate limit for refresh (default: 10/minute)
        AUTH__API_KEY__ENABLED: Enable API Key authentication provider
        AUTH__API_KEY__MAX_PER_USER: Max API keys per user
        AUTH__API_KEY__CREATE_RATE_LIMIT: Rate limit for key creation (default: 5/minute)
        AUTH__API_KEY__DELETE_RATE_LIMIT: Rate limit for key deletion (default: 10/minute)
    """

    enabled: bool = Field(
        default=True,
        description="Master switch for authentication. When False, no auth or user routes registered.",
    )
    jwt: JWTSettings = Field(
        default_factory=JWTSettings,
        description="JWT authentication provider settings",
    )
    api_key: APIKeySettings = Field(
        default_factory=APIKeySettings,
        description="API Key authentication provider settings",
    )
