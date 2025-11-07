"""Authentication-specific exceptions."""

from app.core.exceptions import AuthenticationError, AuthorizationError


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or malformed.

    Attributes:
        message: Error message.
        details: Additional error context.
    """

    def __init__(self, message: str = "Invalid or malformed token") -> None:
        """Initialize InvalidTokenError.

        Args:
            message: Error message describing the invalid token.
        """
        super().__init__(message=message)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired.

    Attributes:
        message: Error message.
        details: Additional error context.
    """

    def __init__(self, message: str = "Token has expired") -> None:
        """Initialize TokenExpiredError.

        Args:
            message: Error message describing the expired token.
        """
        super().__init__(message=message)


class InactiveUserError(AuthorizationError):
    """Raised when user account is inactive.

    Attributes:
        message: Error message.
        details: Additional error context.
    """

    def __init__(
        self, message: str = "User account is inactive", user_id: int | None = None
    ) -> None:
        """Initialize InactiveUserError.

        Args:
            message: Error message describing the inactive account.
            user_id: Optional user ID for context.
        """
        details = {"user_id": user_id} if user_id else None
        super().__init__(message=message, details=details)


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions.

    Attributes:
        message: Error message.
        details: Additional error context.
    """

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_role: str | None = None,
        user_role: str | None = None,
    ) -> None:
        """Initialize InsufficientPermissionsError.

        Args:
            message: Error message describing the permission issue.
            required_role: Role required for the operation.
            user_role: User's current role.
        """
        details = {}
        if required_role:
            details["required_role"] = required_role
        if user_role:
            details["user_role"] = user_role
        super().__init__(message=message, details=details if details else None)
