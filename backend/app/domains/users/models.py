from datetime import UTC, datetime
from enum import StrEnum

from pydantic import EmailStr
from sqlalchemy import Column, DateTime, text
from sqlmodel import Field

from app.core.base.models import IntModel


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
    role: UserRole = UserRole.USER
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
