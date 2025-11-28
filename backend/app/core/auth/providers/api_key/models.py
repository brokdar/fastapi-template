"""API Key database model.

This module defines the database model for storing API keys.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field

from app.core.base.models import IntModel

from .exceptions import InvalidAPIKeyIDError

# =============================================================================
# API KEY ID TYPE CONFIGURATION
# =============================================================================
# To switch to UUID-based API keys:
# 1. Change `type APIKeyID = UUID` and update parse_api_key_id to use UUID()
# 2. Change APIKey to inherit from UUIDModel instead of IntModel
# 3. Run database migration
#
# IMPORTANT: The user_id field must match the User model's ID type.
# If switching users to UUID (in app/domains/users/models.py), also update:
# - user_id: int -> user_id: UUID (line 50)
# - foreign_key="user.id" remains the same
# SQLModel requires concrete types (int/UUID), not type aliases.

type APIKeyID = int


def parse_api_key_id(value: str) -> APIKeyID:
    """Parse string to APIKeyID type.

    Args:
        value: String representation of API key ID.

    Returns:
        Parsed APIKeyID.

    Raises:
        InvalidAPIKeyIDError: If value cannot be parsed to APIKeyID type.
    """
    try:
        return int(value)
    except ValueError as e:
        raise InvalidAPIKeyIDError(
            message=f"Invalid API key ID format: '{value}'",
            value=value,
            expected_type="int",
        ) from e


# =============================================================================


class APIKey(IntModel, table=True):
    """Database model for storing API keys."""

    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    key_hash: str = Field(max_length=255, nullable=False)
    key_prefix: str = Field(max_length=12, index=True, unique=True, nullable=False)
    name: str = Field(min_length=1, max_length=100, nullable=False)
    expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
