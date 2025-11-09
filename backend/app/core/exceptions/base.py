"""Base exception classes for the application.

This module defines a comprehensive exception hierarchy that maps business logic errors
to appropriate HTTP status codes while maintaining clean separation between different
types of errors.
"""

from __future__ import annotations

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


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details,
            headers=headers,
        )


class AuthorizationError(ApplicationError):
    """Raised when user lacks sufficient permissions."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTHORIZATION_ERROR,
            status_code=403,
            details=details,
            headers=headers,
        )


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details,
            headers=headers,
        )


class NotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=404,
            details=details,
            headers=headers,
        )


class ConflictError(ApplicationError):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_CONFLICT,
            status_code=409,
            details=details,
            headers=headers,
        )


class BusinessLogicError(ApplicationError):
    """Raised when business rules are violated."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            status_code=400,
            details=details,
            headers=headers,
        )


class NotImplementedError(ApplicationError):
    """Raised when a requested feature or operation is not implemented."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_IMPLEMENTED,
            status_code=501,
            details=details,
            headers=headers,
        )


class ExternalServiceError(ApplicationError):
    """Raised when external service calls fail."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            status_code=502,
            details=details,
            headers=headers,
        )


class DatabaseError(ApplicationError):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            details=details,
            headers=headers,
        )


class ConfigurationError(ApplicationError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500,
            details=details,
            headers=headers,
        )
