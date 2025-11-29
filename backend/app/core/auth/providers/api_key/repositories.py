"""API Key repository layer.

This module provides data access operations for API key entities.
All database interactions for API keys are handled through this repository.
"""

from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.exceptions import handle_repository_errors
from app.domains.users.models import UserID

from .models import APIKey, APIKeyID


class APIKeyRepository(BaseRepository[APIKey, APIKeyID]):
    """Repository for API key data access operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize APIKeyRepository with database session.

        Args:
            session: Async database session for executing queries.
        """
        super().__init__(session, APIKey)

    @handle_repository_errors()
    async def get_by_prefix(self, prefix: str) -> APIKey | None:
        """Find an API key by its prefix for efficient lookup.

        Args:
            prefix: The key prefix to search for.

        Returns:
            The APIKey if found, None otherwise.
        """
        statement = select(APIKey).where(APIKey.key_prefix == prefix)
        result = await self._session.exec(statement)
        return result.first()

    @handle_repository_errors()
    async def get_by_user_id(self, user_id: UserID) -> list[APIKey]:
        """Get all API keys for a specific user.

        Args:
            user_id: The user's ID to filter by.

        Returns:
            List of API keys belonging to the user.
        """
        statement = select(APIKey).where(APIKey.user_id == user_id)
        result = await self._session.exec(statement)
        return list(result.all())

    @handle_repository_errors()
    async def count_by_user(self, user_id: UserID) -> int:
        """Count API keys for a user (for max limit enforcement).

        Args:
            user_id: The user's ID to count keys for.

        Returns:
            Number of API keys the user has.
        """
        statement = (
            select(func.count()).select_from(APIKey).where(APIKey.user_id == user_id)
        )
        result = await self._session.exec(statement)
        return result.one()

    @handle_repository_errors()
    async def update_last_used(self, key_id: APIKeyID) -> None:
        """Update only the last_used_at timestamp (efficient partial update).

        Args:
            key_id: The API key's ID to update.
        """
        statement = (
            update(APIKey)
            .where(col(APIKey.id) == key_id)
            .values(last_used_at=datetime.now(UTC))
        )
        await self._session.exec(statement)
        await self._session.commit()
