"""User domain-specific exceptions.

This module defines exceptions specific to user management operations.
All exceptions extend ApplicationError and provide domain-specific error handling.
"""

from uuid import UUID

from app.core.exceptions.base import ApplicationError, ErrorCode


class UserNotFoundError(ApplicationError):
    """Raised when a user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        user_id: int | UUID | str | None = None,
    ) -> None:
        """Initialize UserNotFoundError.

        Args:
            message: Error message describing the specific user not found case
            user_id: Optional user identifier for additional context
        """
        details = {"user_id": user_id} if user_id is not None else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details=details,
        )


class UserAlreadyExistsError(ApplicationError):
    """Raised when attempting to create a user that already exists."""

    def __init__(
        self,
        message: str = "User already exists",
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        """Initialize UserAlreadyExistsError.

        Args:
            message: Error message describing the conflict
            field: The field that caused the conflict (e.g., "email", "username")
            value: The conflicting value
        """
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value

        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
            status_code=409,
            details=details,
        )


class InvalidCredentialsError(ApplicationError):
    """Raised when user credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid credentials provided",
    ) -> None:
        """Initialize InvalidCredentialsError.

        Args:
            message: Error message describing the credential issue
        """
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
        )


class InvalidUserIDError(ApplicationError):
    """Raised when user ID parsing or validation fails."""

    def __init__(
        self,
        message: str = "Invalid user ID format",
        value: str | None = None,
        expected_type: str | None = None,
    ) -> None:
        """Initialize InvalidUserIDError.

        Args:
            message: Error message describing the ID parsing failure
            value: The invalid value that failed parsing
            expected_type: The expected ID type (e.g., "int", "UUID")
        """
        details = {}
        if value is not None:
            details["value"] = value
        if expected_type is not None:
            details["expected_type"] = expected_type

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details if details else None,
        )
