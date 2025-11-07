"""Pydantic schemas for error responses.

This module defines type-safe error response models that ensure consistent
error formatting across the API and provide full OpenAPI documentation.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class ErrorDetail(BaseModel):
    """Detailed error information for a single error."""

    code: str = Field(
        description="Machine-readable error code for programmatic handling",
        examples=["RESOURCE_NOT_FOUND"],
    )
    message: str = Field(
        description="Human-readable error message",
        examples=["The requested user was not found"],
    )
    field: str | None = Field(
        default=None,
        description="Field name if the error is related to a specific field",
        examples=["user_id"],
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error context and debugging information"
    )


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information for Pydantic validation failures."""

    field: str = Field(
        description="The field that failed validation", examples=["email"]
    )
    message: str = Field(
        description="Validation error message",
        examples=["value is not a valid email address"],
    )
    type: str = Field(
        description="Type of validation error", examples=["value_error.email"]
    )
    location: list[str | int] = Field(
        description="Location of the error in the input data",
        examples=[["body", "email"]],
    )
    input_value: Any | None = Field(
        default=None, description="The invalid input value that caused the error"
    )


class BaseErrorResponse(BaseModel):
    """Base class for all error response models with common fields and behavior."""

    error: ErrorDetail = Field(description="Error details")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the error occurred (UTC)",
        examples=["2024-01-15T10:30:00+00:00"],
    )
    request_id: str | None = Field(
        default=None,
        description="Unique request identifier for tracing",
        examples=["req_123e4567-e89b-12d3-a456-426614174000"],
    )

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        """Serialize datetime to ISO format string."""
        return dt.isoformat()


class ErrorResponse(BaseErrorResponse):
    """Standard error response model for all API errors."""

    path: str | None = Field(
        default=None,
        description="API endpoint path where the error occurred",
        examples=["/api/v1/users/123"],
    )


class ValidationErrorResponse(BaseErrorResponse):
    """Specialized error response for validation errors."""

    validation_errors: list[ValidationErrorDetail] = Field(
        description="Detailed validation error information", min_length=1
    )
    path: str | None = Field(
        default=None,
        description="API endpoint path where the error occurred",
        examples=["/api/v1/users"],
    )


class InternalServerErrorResponse(BaseErrorResponse):
    """Error response for internal server errors (5xx)."""

    # Override error field description for security context
    error: ErrorDetail = Field(description="Error details (sanitized for security)")

    # Override request_id field description for support context
    request_id: str | None = Field(
        default=None,
        description="Unique request identifier for tracing and support",
        examples=["req_123e4567-e89b-12d3-a456-426614174000"],
    )
