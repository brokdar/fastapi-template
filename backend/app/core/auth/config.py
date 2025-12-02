"""Authentication provider configuration settings."""

import secrets
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr


class JWTSettings(BaseModel):
    """Configuration settings for JWT authentication provider."""

    enabled: bool = Field(
        default=True,
        description="Enable JWT authentication provider.",
    )
    secret_key: Annotated[SecretStr, Field(min_length=32)] = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="Secret key for JWT token signing and verification",
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm (HS256, HS384, HS512, RS256, etc.)",
    )
    access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        description="Access token expiration time in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="Refresh token expiration time in days",
    )


class APIKeySettings(BaseModel):
    """Configuration settings for API Key authentication provider."""

    enabled: bool = Field(
        default=False,
        description="Enable API Key authentication provider.",
    )
    max_per_user: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of API keys allowed per user",
    )
    default_expiration_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Default expiration time in days for newly created API keys",
    )
    header_name: str = Field(
        default="X-API-Key",
        description="HTTP header name used to pass the API key",
    )


class AuthSettings(BaseModel):
    """Authentication configuration for JWT and API Key providers.

    These settings provide convenient defaults and environment variable mapping
    for JWT and API Key authentication, including feature toggles.

    Environment variable examples (with AUTH__ prefix from parent):
        AUTH__ENABLED: Master switch for authentication
        AUTH__JWT__ENABLED: Enable JWT authentication provider
        AUTH__JWT__SECRET_KEY: JWT signing secret
        AUTH__JWT__ALGORITHM: JWT algorithm (default: HS256)
        AUTH__API_KEY__ENABLED: Enable API Key authentication provider
        AUTH__API_KEY__MAX_PER_USER: Max API keys per user
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
