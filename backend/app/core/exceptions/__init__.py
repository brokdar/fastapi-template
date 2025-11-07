"""Exception handling module for the FastAPI application.

This module provides a comprehensive exception handling system with:
- Custom exception hierarchy for business logic errors
- Type-safe error response models
- Global exception handlers for consistent error responses
- Proper error logging without stack trace leakage
"""

from .base import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    ErrorCode,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from .handlers import setup_exception_handlers
from .schemas import (
    ErrorDetail,
    ErrorResponse,
    InternalServerErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

__all__ = [
    # Exception classes
    "ApplicationError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "ConflictError",
    "ConfigurationError",
    "DatabaseError",
    "ErrorCode",
    "ExternalServiceError",
    "NotFoundError",
    "ValidationError",
    # Handler setup
    "setup_exception_handlers",
    # Response schemas
    "ErrorDetail",
    "ErrorResponse",
    "InternalServerErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
]
