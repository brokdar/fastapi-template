"""Generic base repository with strictly typed pagination validation."""

from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.models import IDType
from app.core.pagination.validation import validate_pagination

from .exceptions import (
    EntityNotFoundError,
    handle_repository_errors,
)


class BaseRepository[T, ID: IDType]:
    """Generic base repository for CRUD operations on models with configurable ID types.

    This repository provides type-safe CRUD operations that automatically infer
    the ID type from the model class. Models extending from IntModel will use int IDs,
    while models extending from UUIDModel will use UUID IDs.
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        """Initialize the repository with a database session and model class.

        Args:
            session: Async SQLAlchemy session for database operations
            model_class: The SQLModel class this repository manages
        """
        self._session = session
        self.model_class = model_class

    @handle_repository_errors()
    async def get_by_id(self, id: ID) -> T | None:
        """Retrieve a model instance by its ID.

        Args:
            id: The ID of the model to retrieve (type matches model's ID type)

        Returns:
            The model instance if found, None otherwise

        Raises:
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        return await self._session.get(self.model_class, id)

    @handle_repository_errors()
    async def get_all(self) -> list[T]:
        """Retrieve all model instances.

        Returns:
            List of all model instances

        Raises:
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        statement = select(self.model_class)
        result = await self._session.exec(statement)
        return list(result.all())

    @handle_repository_errors()
    async def count(self) -> int:
        """Count the total number of model instances.

        Returns:
            Total count of model instances

        Raises:
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        statement = select(func.count()).select_from(self.model_class)
        result = await self._session.exec(statement)
        return result.one()

    @handle_repository_errors()
    @validate_pagination
    async def get_paginated(self, offset: int = 0, limit: int = 10) -> list[T]:
        """Retrieve a paginated subset of model instances.

        Args:
            offset: Number of items to skip (default: 0)
            limit: Maximum number of items to return (default: 10)

        Returns:
            List of model instances for the requested page

        Raises:
            InvalidPaginationError: If offset < 0 or limit <= 0
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        statement = select(self.model_class).offset(offset).limit(limit)
        result = await self._session.exec(statement)
        return list(result.all())

    @handle_repository_errors()
    async def create(self, item: T) -> T:
        """Create a new model instance.

        Args:
            item: The model instance to create

        Returns:
            The created model instance with updated fields (e.g., generated ID)

        Raises:
            RepositoryIntegrityError: If integrity constraints are violated
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    @handle_repository_errors()
    async def update(self, item: T) -> T:
        """Update an existing model instance.

        Args:
            item: The model instance to update

        Returns:
            The updated model instance

        Raises:
            RepositoryIntegrityError: If integrity constraints are violated
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        self._session.add(item)
        await self._session.commit()
        await self._session.refresh(item)
        return item

    @handle_repository_errors()
    async def delete(self, id: ID) -> None:
        """Delete a model instance by its ID.

        Args:
            id: The ID of the model to delete (type matches model's ID type)

        Raises:
            EntityNotFoundError: If the entity with the given ID doesn't exist
            RepositoryIntegrityError: If integrity constraints prevent deletion
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        item = await self._session.get(self.model_class, id)
        if not item:
            raise EntityNotFoundError(
                entity_type=self.model_class.__name__,
                entity_id=id,
            )
        await self._session.delete(item)
        await self._session.commit()

    @handle_repository_errors()
    async def filter(self, *conditions: ColumnElement[bool]) -> list[T]:
        """Filter model instances by conditions.

        Args:
            *conditions: SQLAlchemy column expressions returning boolean
                (e.g., Model.field == value)

        Returns:
            Filtered model instances

        Raises:
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        statement = select(self.model_class).where(*conditions)
        result = await self._session.exec(statement)
        return list(result.all())

    @handle_repository_errors()
    @validate_pagination
    async def filter_paginated(
        self, *conditions: ColumnElement[bool], limit: int, offset: int = 0
    ) -> list[T]:
        """Filter and paginate model instances by conditions.

        Args:
            *conditions: SQLAlchemy column expressions returning boolean
                (e.g., Model.field == value)
            limit: Maximum number of instances to retrieve (page size)
            offset: Number of instances to skip from the beginning (default: 0)

        Returns:
            List of filtered model instances for the requested page

        Raises:
            InvalidPaginationError: If limit <= 0 or offset < 0
            RepositoryOperationError: If database operation fails
            RepositoryConnectionError: If database connection fails
        """
        statement = (
            select(self.model_class).where(*conditions).offset(offset).limit(limit)
        )
        result = await self._session.exec(statement)
        return list(result.all())
