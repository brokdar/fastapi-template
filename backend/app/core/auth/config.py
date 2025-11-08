"""Authentication provider configuration settings."""

import secrets
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr


class AuthSettings(BaseModel):
    """Authentication configuration for JWT provider.

    These settings provide convenient defaults and environment variable mapping
    for JWT authentication. Providers are configured and enabled in code via
    dependencies.py, not through configuration.
    """

    JWT_SECRET_KEY: Annotated[SecretStr, Field(min_length=32)] = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="Secret key for JWT token signing and verification",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm (HS256, HS384, HS512, RS256, etc.)",
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=1,
        description="Access token expiration time in minutes",
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        description="Refresh token expiration time in days",
    )
