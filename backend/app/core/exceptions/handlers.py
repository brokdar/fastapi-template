"""Global exception handlers for FastAPI application.

This module implements comprehensive exception handling that catches and transforms
various types of exceptions into standardized HTTP responses while preventing
stack trace leakage and ensuring proper error logging.
"""

import re
import secrets
import traceback
from collections.abc import Callable
from typing import Any, Protocol, cast

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ExceptionHandler

from .base import ApplicationError, ErrorCode
from .schemas import (
    BaseErrorResponse,
    ErrorDetail,
    ErrorResponse,
    InternalServerErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

REQUEST_ID_PREFIX = "req_"
DEFAULT_ERROR_MESSAGE = "An internal server error occurred"
MAX_JSON_DEPTH = 10
MAX_STRING_LENGTH = 200
MAX_BYTES_HEX_LENGTH = 50

STATUS_CODE_TO_ERROR_CODE = {
    401: ErrorCode.AUTHENTICATION_ERROR,
    403: ErrorCode.AUTHORIZATION_ERROR,
    404: ErrorCode.RESOURCE_NOT_FOUND,
    409: ErrorCode.RESOURCE_CONFLICT,
}


class ExceptionHandlerProtocol(Protocol):
    """Protocol for exception handler functions."""

    async def __call__(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle an exception and return a JSON response."""
        ...


def get_error_code_for_status(status_code: int) -> ErrorCode:
    """Map HTTP status code to application error code."""
    if status_code >= 500:
        return ErrorCode.INTERNAL_SERVER_ERROR
    return STATUS_CODE_TO_ERROR_CODE.get(status_code, ErrorCode.INVALID_INPUT)


def _sanitize_development_message(exc: Exception) -> str:
    """Sanitize exception message for development mode to prevent credential leaks.

    Removes potentially sensitive information like passwords, tokens, and file paths
    while preserving useful debugging information.

    Args:
        exc: The exception to sanitize

    Returns:
        Sanitized exception message truncated to 200 characters
    """
    message = str(exc)
    sensitive_patterns = [
        r"password[=:][\w\-\.]+",  # password=value or password:value
        r"token[=:][\w\-\.]+",  # token=value or token:value
        r"key[=:][\w\-\.]+",  # key=value or key:value
        r"secret[=:][\w\-\.]+",  # secret=value or secret:value
        r"/[\w\-\./]+",  # file paths like /path/to/file/
        r"[a-zA-Z]:\\[\\\w\-\.]+",  # Windows paths like C:\path\to\file
    ]

    for pattern in sensitive_patterns:
        message = re.sub(pattern, "[REDACTED]", message, flags=re.IGNORECASE)

    # Truncate to prevent excessive error message sizes
    return message[:200]


def get_request_id(request: Request) -> str:
    """Get request ID from request state or generate a new one.

    The logging middleware should have set this, but we provide a fallback
    to ensure every error response has a request ID.

    Args:
        request: The FastAPI request object

    Returns:
        Request ID string
    """
    request_id: str | None = getattr(request.state, "request_id", None)
    if request_id:
        return request_id

    return f"{REQUEST_ID_PREFIX}{secrets.token_hex(16)}"


# Type handlers for optimized JSON serialization using dispatch pattern
_JSON_TYPE_HANDLERS: dict[type, Callable[[Any], Any]] = {
    str: lambda v: v[:MAX_STRING_LENGTH] if len(v) > MAX_STRING_LENGTH else v,
    int: lambda v: v,
    float: lambda v: v,
    bool: lambda v: v,
    type(None): lambda v: v,
}


def _handle_bytes_value(value: bytes) -> str:
    """Handle bytes values for JSON serialization."""
    try:
        decoded = value.decode("utf-8")
        return (
            decoded[:MAX_STRING_LENGTH] if len(decoded) > MAX_STRING_LENGTH else decoded
        )
    except UnicodeDecodeError:
        hex_repr = value.hex()
        if len(value) > 25:
            return f"<bytes: {hex_repr[:MAX_BYTES_HEX_LENGTH]}...>"
        return f"<bytes: {hex_repr}>"


def _safe_json_value(
    value: Any, max_depth: int = MAX_JSON_DEPTH, current_depth: int = 0
) -> Any:
    """Convert a value to a JSON-serializable format with depth limiting.

    Optimized version using type dispatch pattern for improved performance.
    This function is specifically needed for processing validation error input values
    that may contain complex objects, circular references, or non-serializable types.
    Structlog handles its own serialization, but this is for API response data.
    """
    if current_depth >= max_depth:
        return f"<max_depth_exceeded: {type(value).__name__}>"

    # Fast path for common types using dispatch table
    value_type = type(value)
    handler = _JSON_TYPE_HANDLERS.get(value_type)
    if handler:
        return handler(value)

    # Handle special cases
    if value_type is bytes:
        return _handle_bytes_value(value)
    if value_type in (list, tuple):
        return [_safe_json_value(item, max_depth, current_depth + 1) for item in value]
    if value_type is dict:
        return {
            str(key): _safe_json_value(val, max_depth, current_depth + 1)
            for key, val in value.items()
        }
    # Fallback for other types
    str_repr = str(value)
    return (
        str_repr[:MAX_STRING_LENGTH] if len(str_repr) > MAX_STRING_LENGTH else str_repr
    )


class ExceptionHandlerService:
    """Service class for handling exceptions with dependency injection."""

    def __init__(
        self,
        logger: structlog.BoundLogger,
        settings: Any,
    ):
        self.logger = logger
        self.settings = settings

    def create_error_detail(
        self,
        code: str,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ErrorDetail:
        """Create a standardized error detail object."""
        return ErrorDetail(
            code=code,
            message=message,
            field=field,
            details=details,
        )

    def create_validation_error_detail(
        self,
        field: str,
        message: str,
        error_type: str,
        location: list[str | int],
        input_value: Any = None,
    ) -> ValidationErrorDetail:
        """Create a standardized validation error detail object."""
        return ValidationErrorDetail(
            field=field,
            message=message,
            type=error_type,
            location=location,
            input_value=_safe_json_value(input_value),
        )

    def process_validation_errors(
        self, errors: list[dict[str, Any]]
    ) -> list[ValidationErrorDetail]:
        """Process validation errors into standardized format."""
        return [
            self.create_validation_error_detail(
                field=" -> ".join(str(x) for x in error["loc"]),
                message=error["msg"],
                error_type=error["type"],
                location=list(error["loc"]),
                input_value=error.get("input"),
            )
            for error in errors
        ]

    async def create_error_response(
        self,
        request: Request,
        status_code: int,
        error_detail: ErrorDetail,
        request_id: str | None = None,
        extra_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        """Create a standardized error response."""
        if not request_id:
            request_id = get_request_id(request)

        # Determine response class based on extra_data and status code
        response_data: BaseErrorResponse
        if extra_data and "validation_errors" in extra_data:
            response_data = ValidationErrorResponse(
                error=error_detail,
                validation_errors=extra_data["validation_errors"],
                request_id=request_id,
                path=str(request.url.path),
            )
        elif status_code >= 500:
            response_data = InternalServerErrorResponse(
                error=error_detail,
                request_id=request_id,
            )
        else:
            response_data = ErrorResponse(
                error=error_detail,
                request_id=request_id,
                path=str(request.url.path),
            )

        return JSONResponse(
            status_code=status_code,
            content=response_data.model_dump(),
            headers=headers,
        )

    def log_error(
        self,
        level: str,
        message: str,
        request: Request,
        request_id: str,
        extra_info: dict[str, Any] | None = None,
    ) -> None:
        """Log error with structured format using structlog."""
        # Check if username is available in request state (set by session middleware)
        username = getattr(request.state, "username", None)

        log_data: dict[str, Any] = {
            "request_id": request_id,
            "path": str(request.url.path),
            "method": request.method,
        }

        # Add username if available
        if username:
            log_data["username"] = username

        log = self.logger.bind(**log_data)

        if extra_info:
            log = log.bind(**extra_info)

        log_method = getattr(log, level.lower(), log.info)
        log_method(message)


logger = structlog.get_logger("exceptions")
exception_service: ExceptionHandlerService | None = None


def _get_exception_service() -> ExceptionHandlerService:
    """Get or create the global exception service."""
    global exception_service
    if exception_service is None:
        from app.config import get_settings

        settings = get_settings()
        exception_service = ExceptionHandlerService(logger, settings)
    return exception_service


async def _process_validation_errors(
    request: Request,
    errors: list[dict[str, Any]],
    error_context: str,
    error_message: str = "Request validation failed",
) -> JSONResponse:
    """Process validation errors with unified logic for both FastAPI and Pydantic validation errors.

    Args:
        request: The FastAPI request object
        errors: List of error dictionaries from pydantic/FastAPI
        error_context: Context description for logging (e.g., "Validation error on GET /api/users")
        error_message: Custom error message for the response

    Returns:
        Standardized JSON error response
    """
    request_id = get_request_id(request)
    validation_errors = _get_exception_service().process_validation_errors(errors)

    _get_exception_service().log_error(
        level="warning",
        message=error_context,
        request=request,
        request_id=request_id,
        extra_info={
            "validation_errors": [
                {
                    "field": err.field,
                    "message": err.message,
                    "type": err.type,
                }
                for err in validation_errors
            ],
            "error_count": len(validation_errors),
        },
    )

    error_detail = _get_exception_service().create_error_detail(
        code=ErrorCode.VALIDATION_ERROR.value,
        message=error_message,
        details={"error_count": len(validation_errors)},
    )

    return await _get_exception_service().create_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_detail=error_detail,
        request_id=request_id,
        extra_data={"validation_errors": validation_errors},
    )


async def application_error_handler(
    request: Request, exc: ApplicationError
) -> JSONResponse:
    """Handle custom application errors with proper response formatting."""
    request_id = get_request_id(request)
    _get_exception_service().log_error(
        level="error",
        message=f"Application error: {exc.error_code.value} - {exc.message}",
        request=request,
        request_id=request_id,
        extra_info={
            "error_code": exc.error_code.value,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    error_detail = _get_exception_service().create_error_detail(
        code=exc.error_code.value,
        message=exc.message,
        details=exc.details if exc.details else None,
    )

    return await _get_exception_service().create_error_response(
        request=request,
        status_code=exc.status_code,
        error_detail=error_detail,
        request_id=request_id,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    error_dicts = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        }
        for error in exc.errors()
    ]

    return await _process_validation_errors(
        request=request,
        errors=error_dicts,
        error_context=f"Validation error on {request.method} {request.url.path}",
        error_message="Request validation failed",
    )


async def pydantic_validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle direct Pydantic validation errors (not from FastAPI request validation)."""
    error_dicts = [
        {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"],
            "input": error.get("input"),
        }
        for error in exc.errors()
    ]

    return await _process_validation_errors(
        request=request,
        errors=error_dicts,
        error_context=f"Pydantic validation error: {len(error_dicts)} field(s) failed validation",
        error_message="Data validation failed",
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions with consistent formatting."""
    request_id = get_request_id(request)
    error_code = get_error_code_for_status(exc.status_code)

    log_level = "error" if exc.status_code >= 500 else "warning"
    _get_exception_service().log_error(
        level=log_level,
        message=f"HTTP {exc.status_code} error: {exc.detail}",
        request=request,
        request_id=request_id,
        extra_info={
            "status_code": exc.status_code,
            "error_detail": exc.detail,
        },
    )

    error_detail = _get_exception_service().create_error_detail(
        code=error_code.value,
        message=str(exc.detail),
    )

    return await _get_exception_service().create_error_response(
        request=request,
        status_code=exc.status_code,
        error_detail=error_detail,
        request_id=request_id,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with secure error reporting."""
    request_id = get_request_id(request)
    is_development = _get_exception_service().settings.ENVIRONMENT == "development"

    _get_exception_service().log_error(
        level="error",
        message=f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        request=request,
        request_id=request_id,
        extra_info={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "stack_trace": traceback.format_exc() if is_development else None,
        },
    )

    error_detail = _get_exception_service().create_error_detail(
        code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        message=DEFAULT_ERROR_MESSAGE
        if not is_development
        else _sanitize_development_message(exc),
        details={"exception_type": type(exc).__name__} if is_development else None,
    )

    return await _get_exception_service().create_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_detail=error_detail,
        request_id=request_id,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    # Custom application errors (highest priority)
    app.add_exception_handler(
        ApplicationError, cast(ExceptionHandler, application_error_handler)
    )
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, validation_error_handler)
    )
    app.add_exception_handler(
        ValidationError, cast(ExceptionHandler, pydantic_validation_error_handler)
    )
    app.add_exception_handler(
        StarletteHTTPException, cast(ExceptionHandler, http_exception_handler)
    )
    # Catch-all for unexpected exceptions (lowest priority)
    app.add_exception_handler(
        Exception, cast(ExceptionHandler, general_exception_handler)
    )
