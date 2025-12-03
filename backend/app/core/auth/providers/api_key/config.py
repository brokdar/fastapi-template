"""API Key authentication provider configuration settings."""

from pydantic import BaseModel, Field


class APIKeySettings(BaseModel):
    """Configuration settings for API Key authentication provider.

    Attributes:
        enabled: Enable API Key authentication provider.
        max_per_user: Maximum number of API keys allowed per user.
        default_expiration_days: Default expiration time in days for new API keys.
        header_name: HTTP header name used to pass the API key.
        create_rate_limit: Rate limit for API key creation endpoint.
        delete_rate_limit: Rate limit for API key deletion endpoint.
    """

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
    create_rate_limit: str = Field(
        default="5/minute",
        description="Rate limit for API key creation endpoint",
    )
    delete_rate_limit: str = Field(
        default="10/minute",
        description="Rate limit for API key deletion endpoint",
    )
