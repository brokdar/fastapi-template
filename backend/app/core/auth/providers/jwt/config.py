"""JWT authentication provider configuration settings."""

import secrets
from typing import Annotated, Literal

from pydantic import BaseModel, Field, SecretStr

JWTAlgorithm = Literal["HS256", "HS384", "HS512"]


class JWTSettings(BaseModel):
    """Configuration settings for JWT authentication provider.

    Attributes:
        enabled: Enable JWT authentication provider.
        secret_key: Secret key for JWT token signing and verification.
        algorithm: JWT signing algorithm (HS256, HS384, HS512).
        access_token_expire_minutes: Access token expiration time in minutes.
        refresh_token_expire_days: Refresh token expiration time in days.
        login_rate_limit: Rate limit for login endpoint.
        refresh_rate_limit: Rate limit for token refresh endpoint.
    """

    enabled: bool = Field(
        default=True,
        description="Enable JWT authentication provider.",
    )
    secret_key: Annotated[SecretStr, Field(min_length=32)] = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(32)),
        description="Secret key for JWT token signing and verification",
    )
    algorithm: JWTAlgorithm = Field(
        default="HS256",
        description="JWT signing algorithm (HS256, HS384, HS512)",
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
    login_rate_limit: str = Field(
        default="5/minute",
        description="Rate limit for login endpoint (e.g., '5/minute', '100/hour')",
    )
    refresh_rate_limit: str = Field(
        default="10/minute",
        description="Rate limit for token refresh endpoint",
    )
