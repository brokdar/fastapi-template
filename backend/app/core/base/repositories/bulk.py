"""Bulk operations mixin for repository pattern.

Provides bulk_create, bulk_delete, and bulk_upsert operations optimized for PostgreSQL.

Performance: Uses RETURNING + populate_existing for batch refresh (2 queries vs N+1).
For 50 items: 50x fewer queries compared to individual refresh() calls.

References:
    https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html (populate_existing)
    https://github.com/sqlalchemy/sqlalchemy/discussions/11488 (bulk operations)
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.dialects.postgresql.dml import Insert as PostgreSQLInsert
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.models import BaseModel

from .exceptions import handle_repository_errors


class BulkOperationsMixin[T: BaseModel[Any], ID: int | UUID]:
    """Mixin class providing bulk operations for repository classes.

    This mixin adds bulk_create, bulk_delete, and bulk_upsert operations
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

        Uses PostgreSQL's RETURNING clause to fetch generated IDs in a single
        INSERT statement, then batch refreshes all objects with a single SELECT
        query using populate_existing for optimal performance.

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

        stmt = insert(self.model_class).values(item_dicts).returning(self.model_class)
        result = await self._session.scalars(stmt)

        created_items = list(result.all())
        await self._session.commit()

        if created_items:
            # Batch refresh: 1 query instead of N refresh() calls
            # populate_existing updates objects in session's identity map
            id_field = self.model_class.id
            if id_field is not None:
                refresh_stmt = (
                    select(self.model_class)
                    .where(id_field.in_([item.id for item in created_items]))
                    .execution_options(populate_existing=True)
                )
                # execute() required for execution_options (populate_existing)
                await self._session.execute(refresh_stmt)

        return created_items

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
            # execute() appropriate for DELETE (no scalars returned)
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

        Uses PostgreSQL's RETURNING clause to fetch the final state in a single
        statement, then batch refreshes all objects with a single SELECT query
        using populate_existing for optimal performance.

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
            PostgreSQLInsert,
            insert(self.model_class).values(item_dicts).returning(self.model_class),
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

        result = await self._session.scalars(upsert_stmt)

        upserted_items = list(result.all())
        await self._session.commit()

        if upserted_items:
            # Batch refresh: critical for upserts to update existing objects in identity map
            id_field = self.model_class.id
            if id_field is not None:
                refresh_stmt = (
                    select(self.model_class)
                    .where(id_field.in_([item.id for item in upserted_items]))
                    .execution_options(populate_existing=True)
                )
                # execute() required for execution_options (populate_existing)
                await self._session.execute(refresh_stmt)

        return upserted_items
