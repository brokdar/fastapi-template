"""API Key authentication exceptions.

This module defines exceptions specific to API key operations.
All exceptions extend ApplicationError and provide domain-specific error handling.
"""

from app.core.exceptions.base import ApplicationError, ErrorCode


class APIKeyNotFoundError(ApplicationError):
    """Raised when an API key is not found."""

    def __init__(
        self,
        message: str = "API key not found",
        key_id: int | None = None,
    ) -> None:
        """Initialize APIKeyNotFoundError.

        Args:
            message: Error message describing the specific API key not found case.
            key_id: Optional API key identifier for additional context.
        """
        details: dict[str, int] = {"key_id": key_id} if key_id is not None else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details=details,
        )


class APIKeyLimitExceededError(ApplicationError):
    """Raised when user has reached maximum API keys limit."""

    def __init__(
        self,
        message: str = "Maximum API keys limit reached",
        max_allowed: int | None = None,
        current_count: int | None = None,
    ) -> None:
        """Initialize APIKeyLimitExceededError.

        Args:
            message: Error message describing the limit exceeded case.
            max_allowed: Maximum number of API keys allowed.
            current_count: Current number of API keys the user has.
        """
        details: dict[str, int] = {}
        if max_allowed is not None:
            details["max_allowed"] = max_allowed
        if current_count is not None:
            details["current_count"] = current_count

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details,
        )


class APIKeyExpiredError(ApplicationError):
    """Raised when an API key has expired."""

    def __init__(
        self,
        message: str = "API key has expired",
        key_id: int | None = None,
    ) -> None:
        """Initialize APIKeyExpiredError.

        Args:
            message: Error message describing the expiration.
            key_id: Optional API key identifier for additional context.
        """
        details: dict[str, int] = {"key_id": key_id} if key_id is not None else {}
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details,
        )


class InvalidAPIKeyError(ApplicationError):
    """Raised when an API key is invalid."""

    def __init__(
        self,
        message: str = "Invalid API key",
        key_prefix: str | None = None,
    ) -> None:
        """Initialize InvalidAPIKeyError.

        Args:
            message: Error message describing the invalid key.
            key_prefix: Optional key prefix for debugging (safe to log, not the full key).
        """
        details: dict[str, str] = {}
        if key_prefix is not None:
            details["key_prefix"] = key_prefix

        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details,
        )
