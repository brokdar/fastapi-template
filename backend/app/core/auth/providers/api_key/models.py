"""API Key database model.

This module defines the database model for storing API keys.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field

from app.core.base.models import BaseModel


class APIKey(BaseModel, table=True):
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
