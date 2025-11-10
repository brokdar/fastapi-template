"""ID parsing mixins for UserService composition.

This module provides mixin classes that implement ID parsing logic for different
ID types. Following the FastAPI-Users pattern, these mixins are composed with
UserService to provide concrete parse_id implementations resolved via Python's
Method Resolution Order (MRO).

Example:
    >>> class IntUserService(IntIDMixin, UserService[int]):
    ...     pass
    >>> service = IntUserService(repository, password_service)
    >>> user_id = service.parse_id("123")  # Returns: 123 (int)
"""

from typing import Any
from uuid import UUID

from .exceptions import InvalidUserIDError


class IntIDMixin:
    """Mixin providing integer ID parsing implementation.

    When composed with UserService via multiple inheritance, provides the
    parse_id implementation for integer-based user IDs with strict validation.

    The mixin must be listed BEFORE UserService in the inheritance order to
    ensure Python's MRO resolves parse_id to this implementation.

    Example:
        >>> class IntUserService(IntIDMixin, UserService[int]):
        ...     pass

    Validation rules:
        - Accepts integers (passthrough)
        - Accepts strings convertible to integers
        - Rejects floats explicitly (prevents precision loss)
        - Rejects non-numeric strings
    """

    def parse_id(self, value: Any) -> int:
        """Parse value to integer ID with strict validation.

        Args:
            value: Value to parse, typically a string from JWT token.

        Returns:
            Valid integer ID.

        Raises:
            InvalidUserIDError: If value cannot be parsed as integer or is a float.
        """
        if isinstance(value, int):
            return value

        if isinstance(value, float):
            raise InvalidUserIDError(
                message="Float values not allowed for integer user IDs",
                value=str(value),
                expected_type="int",
            )

        try:
            return int(value)
        except (ValueError, TypeError) as e:
            raise InvalidUserIDError(
                message=f"Cannot parse value as integer ID: {value!r}",
                value=str(value),
                expected_type="int",
            ) from e


class UUIDIDMixin:
    """Mixin providing UUID ID parsing implementation.

    When composed with UserService via multiple inheritance, provides the
    parse_id implementation for UUID-based user IDs with validation.

    The mixin must be listed BEFORE UserService in the inheritance order to
    ensure Python's MRO resolves parse_id to this implementation.

    Example:
        >>> class UUIDUserService(UUIDIDMixin, UserService[UUID]):
        ...     pass

    Validation rules:
        - Accepts UUID instances (passthrough)
        - Accepts strings in valid UUID format
        - Converts values to strings before parsing
        - Rejects invalid UUID formats
    """

    def parse_id(self, value: Any) -> UUID:
        """Parse value to UUID with validation.

        Args:
            value: Value to parse, typically a string from JWT token.

        Returns:
            Valid UUID instance.

        Raises:
            InvalidUserIDError: If value cannot be parsed as UUID.
        """
        if isinstance(value, UUID):
            return value

        try:
            return UUID(str(value))
        except (ValueError, TypeError, AttributeError) as e:
            raise InvalidUserIDError(
                message=f"Cannot parse value as UUID: {value!r}",
                value=str(value),
                expected_type="UUID",
            ) from e
