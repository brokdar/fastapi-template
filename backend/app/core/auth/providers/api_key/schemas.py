"""Pydantic schemas for API key authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.users.models import UserID

from .models import APIKeyID


class APIKeyCreate(BaseModel):
    """Request schema for creating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for the API key",
    )
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Custom expiration in days (uses default if not set)",
    )


class APIKeyResponse(BaseModel):
    """Response schema for API key metadata (excludes secret)."""

    id: APIKeyID
    name: str
    key_prefix: str = Field(..., description="First 12 chars (e.g., 'sk_a1b2c3d4e5')")
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(APIKeyResponse):
    """Response schema for newly created API key (includes secret)."""

    secret_key: str = Field(
        ..., description="Full API key (shown only once at creation)"
    )


class APIKeyListResponse(BaseModel):
    """Response schema for admin listing of API keys with user context."""

    id: APIKeyID
    user_id: UserID
    name: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
