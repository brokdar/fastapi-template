"""User domain-specific exceptions.

This module defines exceptions specific to user management operations.
All exceptions extend ApplicationError and provide domain-specific error handling.
"""

from app.core.exceptions.base import ApplicationError, ErrorCode


class UserNotFoundError(ApplicationError):
    """Raised when a user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        user_id: int | str | None = None,
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
