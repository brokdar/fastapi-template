"""Bulk operations mixin for repository pattern.

This module provides a BulkOperationsMixin class that can be used by repositories
that require bulk operations. It leverages SQLAlchemy 2.0's modern bulk operations
for optimal performance on PostgreSQL.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.dialects.postgresql.dml import Insert as PostgreSQLInsert
from sqlmodel import delete, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.models import BaseModel

from .exceptions import handle_repository_errors


class BulkOperationsMixin[T: BaseModel[Any], ID: int | UUID]:
    """Mixin class providing bulk operations for repository classes.

    This mixin adds bulk create, update, delete, and upsert operations
    to any repository class that includes it. All operations are transactional
    and will rollback on failure.

    The mixin expects the including class to have:
    - session: AsyncSession attribute
    - model_class: type[T] attribute
    """

    _session: AsyncSession
    model_class: type[T]

    def _prepare_item_dict(self, item: T) -> dict[str, Any]:
        """Convert a model instance to a dictionary, excluding None IDs.

        Args:
            item: Model instance to convert

        Returns:
            Dictionary representation with None IDs removed
        """
        item_dict = item.model_dump(exclude_unset=True)
        if item_dict.get("id") is None:
            item_dict.pop("id", None)
        return item_dict

    @handle_repository_errors()
    async def bulk_create(self, items: list[T]) -> list[T]:
        """Create multiple model instances in a single operation.

        Args:
            items: List of model instances to create

        Returns:
            List of created model instances with generated IDs

        Raises:
            RepositoryIntegrityError: If integrity constraints are violated
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        if not items:
            return []

        item_dicts = [self._prepare_item_dict(item) for item in items]

        # Use modern SQLAlchemy 2.0 bulk insert with RETURNING
        stmt = insert(self.model_class).returning(self.model_class)
        result = await self._session.scalars(stmt, item_dicts)

        created_items = list(result.all())
        await self._session.commit()

        return created_items

    @handle_repository_errors()
    async def bulk_update(self, items: list[T]) -> list[T]:
        """Update multiple model instances by their primary keys.

        Args:
            items: List of model instances to update (must have IDs set)

        Returns:
            List of updated model instances

        Raises:
            RepositoryIntegrityError: If integrity constraints are violated
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        if not items:
            return []

        update_dicts = []
        for item in items:
            if item.id is None:
                msg = f"Cannot update {self.model_class.__name__} without ID"
                raise ValueError(msg)
            update_dicts.append(item.model_dump())

        stmt = update(self.model_class).returning(self.model_class)
        result = await self._session.scalars(stmt, update_dicts)
        updated_items = list(result.all())
        await self._session.commit()

        return updated_items

    @handle_repository_errors()
    async def bulk_delete(self, ids: list[ID]) -> None:
        """Delete multiple model instances by their IDs.

        Args:
            ids: List of primary key IDs to delete

        Raises:
            RepositoryIntegrityError: If integrity constraints prevent deletion
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        if not ids:
            return

        id_field = self.model_class.id
        if id_field is not None:
            stmt = delete(self.model_class).where(id_field.in_(ids))
            await self._session.execute(stmt)

        await self._session.commit()

    @handle_repository_errors()
    async def bulk_upsert(
        self,
        items: list[T],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> list[T]:
        """Insert or update multiple model instances using PostgreSQL's ON CONFLICT.

        Args:
            items: List of model instances to upsert
            conflict_columns: List of column names that define the conflict target
            update_columns: Specific columns to update on conflict (default: all except ID)

        Returns:
            List of upserted model instances

        Raises:
            RepositoryIntegrityError: If integrity constraints are violated
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        if not items:
            return []

        item_dicts = [self._prepare_item_dict(item) for item in items]

        pg_stmt = cast(
            PostgreSQLInsert, insert(self.model_class).returning(self.model_class)
        )

        if update_columns is None:
            all_columns = set(self.model_class.model_fields.keys())
            excluded_columns = set(conflict_columns) | {"id"}
            update_columns = list(all_columns - excluded_columns)

        if not update_columns:
            all_columns = set(self.model_class.model_fields.keys())
            excluded_columns = set(conflict_columns)
            update_columns = list(all_columns - excluded_columns)

        if not update_columns:
            update_columns = list(self.model_class.model_fields.keys())

        update_dict = {col: getattr(pg_stmt.excluded, col) for col in update_columns}
        upsert_stmt = pg_stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_dict,
        )

        result = await self._session.scalars(upsert_stmt, item_dicts)

        upserted_items = list(result.all())
        await self._session.commit()

        return upserted_items
