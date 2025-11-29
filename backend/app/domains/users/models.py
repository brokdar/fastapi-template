from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeAlias

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, Enum, text
from sqlmodel import Field

from app.core.base.models import IntModel
from app.domains.users.exceptions import InvalidUserIDError

# =============================================================================
# USER ID TYPE CONFIGURATION
# =============================================================================
# To switch to UUID-based users:
# 1. Change `UserID: TypeAlias = UUID` and update parse_user_id to use UUID()
# 2. Change User to inherit from UUIDModel instead of IntModel
# 3. Run database migration
#
# Note: We use TypeAlias (PEP 613) instead of `type` (PEP 695) because
# SQLModel's type resolution uses issubclass() which doesn't work with
# PEP 695 TypeAliasType objects. See: github.com/fastapi/sqlmodel/discussions/1204

UserID: TypeAlias = int  # noqa: UP040 - SQLModel requires TypeAlias, not PEP 695


def parse_user_id(value: str) -> UserID:
    """Parse string to UserID type.

    Args:
        value: String representation of user ID.

    Returns:
        Parsed UserID.

    Raises:
        InvalidUserIDError: If value cannot be parsed to UserID type.
    """
    try:
        return int(value)
    except ValueError as e:
        raise InvalidUserIDError(
            message=f"Invalid user ID format: '{value}'",
            value=value,
            expected_type="int",
        ) from e


# =============================================================================


class UserRole(StrEnum):
    """Basic role definitions."""

    USER = "user"
    ADMIN = "admin"


class User(IntModel, table=True):
    """User model in the database."""

    username: str = Field(
        unique=True, index=True, min_length=3, max_length=12, regex=r"^[a-zA-Z0-9_]+$"
    )
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(
            Enum(
                UserRole,
                name="userrole",
                values_callable=lambda obj: [e.value for e in obj],
            )
        ),
    )
    is_active: bool = True
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
            server_onupdate=text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    @property
    def full_name(self) -> str:
        """Get the user's full name from first and last name."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else ""
