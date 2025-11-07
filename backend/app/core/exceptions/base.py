"""Base exception classes for the application.

This module defines a comprehensive exception hierarchy that maps business logic errors
to appropriate HTTP status codes while maintaining clean separation between different
types of errors.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    """Standardized error codes for consistent error identification."""

    # Authentication & Authorization (4xx)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"

    # Validation & Input Errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Resource Errors (4xx)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Business Logic Errors (4xx)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    INVALID_STATE = "INVALID_STATE"

    # Implementation Errors (5xx)
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

    # External Service Errors (5xx)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"

    # Database Errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"

    # System Errors (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ApplicationError(Exception):
    """Base exception class for all application-specific exceptions.

    This class provides a consistent interface for all custom exceptions
    and includes metadata for proper HTTP response generation.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            error_code: Standardized error code for identification
            status_code: HTTP status code to return
            details: Additional error details for debugging
            headers: Optional HTTP headers to include in response
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers or {}

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return f"{self.error_code.value}: {self.message}"

    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code={self.error_code.value}, "
            f"status_code={self.status_code})"
        )


# Exception configuration factory pattern to eliminate code duplication
_EXCEPTION_CONFIGS = {
    "AuthenticationError": (
        ErrorCode.AUTHENTICATION_ERROR,
        401,
        "Authentication failed",
    ),
    "AuthorizationError": (
        ErrorCode.AUTHORIZATION_ERROR,
        403,
        "Insufficient permissions",
    ),
    "ValidationError": (ErrorCode.VALIDATION_ERROR, 422, "Validation failed"),
    "NotFoundError": (ErrorCode.RESOURCE_NOT_FOUND, 404, "Resource not found"),
    "ConflictError": (ErrorCode.RESOURCE_CONFLICT, 409, "Resource conflict"),
    "BusinessLogicError": (
        ErrorCode.BUSINESS_RULE_VIOLATION,
        400,
        "Business rule violation",
    ),
    "NotImplementedError": (ErrorCode.NOT_IMPLEMENTED, 501, "Feature not implemented"),
    "ExternalServiceError": (
        ErrorCode.EXTERNAL_SERVICE_ERROR,
        502,
        "External service error",
    ),
    "DatabaseError": (ErrorCode.DATABASE_ERROR, 500, "Database error"),
    "ConfigurationError": (ErrorCode.CONFIGURATION_ERROR, 500, "Configuration error"),
}


def _create_exception_init(
    default_error_code: ErrorCode, status_code: int, default_message: str
) -> Callable[..., None]:
    """Factory function to create exception __init__ methods with consistent behavior."""

    def init_method(
        self: ApplicationError,
        message: str = default_message,
        error_code: ErrorCode = default_error_code,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        ApplicationError.__init__(
            self,
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            headers=headers,
        )

    return init_method


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["AuthenticationError"])


class AuthorizationError(ApplicationError):
    """Raised when user lacks sufficient permissions."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["AuthorizationError"])


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["ValidationError"])


class NotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["NotFoundError"])


class ConflictError(ApplicationError):
    """Raised when a resource conflict occurs."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["ConflictError"])


class BusinessLogicError(ApplicationError):
    """Raised when business rules are violated."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["BusinessLogicError"])


class NotImplementedError(ApplicationError):
    """Raised when a requested feature or operation is not implemented."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["NotImplementedError"])


class ExternalServiceError(ApplicationError):
    """Raised when external service calls fail."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["ExternalServiceError"])


class DatabaseError(ApplicationError):
    """Raised when database operations fail."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["DatabaseError"])


class ConfigurationError(ApplicationError):
    """Raised when configuration is invalid or missing."""

    __init__ = _create_exception_init(*_EXCEPTION_CONFIGS["ConfigurationError"])
