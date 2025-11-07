"""Repository-specific exception classes and error handling decorators.

This module provides a comprehensive error handling system for repository operations,
extending the application's base exception hierarchy to handle database-specific
failures with proper context and meaningful error messages.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import structlog
from sqlalchemy import exc as sqlalchemy_exc

from app.core.exceptions.base import (
    ConflictError,
    DatabaseError,
    NotFoundError,
)

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class RepositoryError(DatabaseError):
    """Base exception for all repository-specific errors.

    Extends DatabaseError to provide a specialized exception hierarchy
    for database repository operations.
    """

    def __init__(
        self,
        message: str = "Repository operation failed",
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize repository error with database context.

        Args:
            message: Human-readable error message
            details: Additional error context for debugging
            headers: Optional HTTP headers
        """
        super().__init__(
            message=message,
            details=details,
            headers=headers,
        )


class EntityNotFoundError(NotFoundError):
    """Raised when a requested entity is not found in the database.

    This exception provides specific context about the entity type and ID
    that was not found, making it easier to debug and handle in client code.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize entity not found error.

        Args:
            entity_type: The type/class name of the entity
            entity_id: The ID that was not found
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"{entity_type} with ID {entity_id!r} not found"
        enhanced_details = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )


class RepositoryOperationError(RepositoryError):
    """Raised when a general database operation fails.

    Used for database operations that don't fall into more specific categories
    like integrity violations or connection issues.
    """

    def __init__(
        self,
        operation: str,
        entity_type: str,
        original_error: Exception,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize repository operation error.

        Args:
            operation: The operation that failed (e.g., 'create', 'update')
            entity_type: The type/class name of the entity
            original_error: The original SQLAlchemy exception
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"Database operation '{operation}' failed for {entity_type}: {original_error}"
        enhanced_details = {
            "operation": operation,
            "entity_type": entity_type,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )


class RepositoryIntegrityError(ConflictError):
    """Raised when database integrity constraints are violated.

    This includes unique constraint violations, foreign key constraint violations,
    and check constraint violations. Maps to HTTP 409 Conflict status.
    """

    def __init__(
        self,
        constraint_type: str,
        entity_type: str,
        original_error: sqlalchemy_exc.IntegrityError,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize repository integrity error.

        Args:
            constraint_type: The type of constraint violated
            entity_type: The type/class name of the entity
            original_error: The original SQLAlchemy IntegrityError
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"Integrity constraint violation for {entity_type}: {constraint_type} constraint failed"
        enhanced_details = {
            "constraint_type": constraint_type,
            "entity_type": entity_type,
            "original_error": str(original_error),
            "statement": getattr(original_error, "statement", None),
            "params": getattr(original_error, "params", None),
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )


class RepositoryConnectionError(RepositoryError):
    """Raised when database connection issues occur.

    This includes connection timeouts, connection pool exhaustion,
    and other network-related database connectivity issues.
    """

    def __init__(
        self,
        operation: str,
        original_error: Exception,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize repository connection error.

        Args:
            operation: The operation that failed due to connection issues
            original_error: The original connection-related exception
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"Database connection failed during '{operation}': {original_error}"
        enhanced_details = {
            "operation": operation,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )


class BulkOperationError(RepositoryError):
    """Raised when bulk operations fail.

    This exception provides context about bulk database operations that fail,
    including the operation type and number of items affected.
    """

    def __init__(
        self,
        operation: str,
        entity_type: str,
        items_count: int,
        original_error: Exception,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize bulk operation error.

        Args:
            operation: The bulk operation that failed (e.g., 'bulk_create')
            entity_type: The type/class name of the entities
            items_count: Number of items in the failed bulk operation
            original_error: The original exception that caused the failure
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"Bulk operation '{operation}' failed for {items_count} {entity_type} items: {original_error}"
        enhanced_details = {
            "operation": operation,
            "entity_type": entity_type,
            "items_count": items_count,
            "original_error": str(original_error),
            "original_error_type": type(original_error).__name__,
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )


def handle_repository_errors(
    entity_type: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator to handle SQLAlchemy exceptions and convert them to custom exceptions.

    This decorator catches common SQLAlchemy exceptions and transforms them into
    our custom exception hierarchy with proper context and error messages.

    Args:
        entity_type: The entity type name for error context (auto-detected if None)

    Returns:
        Decorated function with error handling

    Example:
        ```python
        @handle_repository_errors("User")
        async def create_user(self, user: User) -> User:
            # Database operations that may fail
            pass
        ```
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            operation = func.__name__
            detected_entity_type = entity_type

            # Auto-detect entity type from repository instance if not provided
            if not detected_entity_type and args and hasattr(args[0], "model_class"):
                model_class = args[0].model_class
                # For classes, use their __name__ attribute directly
                detected_entity_type = model_class.__name__

            try:
                return await func(*args, **kwargs)
            except sqlalchemy_exc.IntegrityError as e:
                # Determine constraint type from error message
                error_msg = str(e).lower()
                if "unique" in error_msg or "duplicate" in error_msg:
                    constraint_type = "unique"
                elif "foreign key" in error_msg or "fk_" in error_msg:
                    constraint_type = "foreign key"
                elif "check" in error_msg:
                    constraint_type = "check"
                else:
                    constraint_type = "integrity"

                logger.warning(
                    "repository_integrity_constraint_violation",
                    operation=operation,
                    entity_type=detected_entity_type,
                    constraint_type=constraint_type,
                    error=str(e),
                )

                raise RepositoryIntegrityError(
                    constraint_type=constraint_type,
                    entity_type=detected_entity_type or "Unknown",
                    original_error=e,
                ) from e

            except sqlalchemy_exc.OperationalError as e:
                # Connection and operational errors
                error_msg = str(e).lower()
                if any(
                    keyword in error_msg
                    for keyword in ["connection", "timeout", "network"]
                ):
                    logger.error(
                        "repository_connection_error",
                        operation=operation,
                        entity_type=detected_entity_type,
                        error=str(e),
                    )
                    raise RepositoryConnectionError(
                        operation=operation,
                        original_error=e,
                    ) from e
                logger.error(
                    "repository_operational_error",
                    operation=operation,
                    entity_type=detected_entity_type,
                    error=str(e),
                )
                raise RepositoryOperationError(
                    operation=operation,
                    entity_type=detected_entity_type or "Unknown",
                    original_error=e,
                ) from e

            except sqlalchemy_exc.DatabaseError as e:
                # Generic database errors
                logger.error(
                    "repository_database_error",
                    operation=operation,
                    entity_type=detected_entity_type,
                    error=str(e),
                )
                raise RepositoryOperationError(
                    operation=operation,
                    entity_type=detected_entity_type or "Unknown",
                    original_error=e,
                ) from e

            except sqlalchemy_exc.StatementError as e:
                # SQL statement errors
                logger.error(
                    "repository_statement_error",
                    operation=operation,
                    entity_type=detected_entity_type,
                    statement=getattr(e, "statement", None),
                    params=getattr(e, "params", None),
                    error=str(e),
                )
                raise RepositoryOperationError(
                    operation=operation,
                    entity_type=detected_entity_type or "Unknown",
                    original_error=e,
                ) from e

        return wrapper

    return decorator
