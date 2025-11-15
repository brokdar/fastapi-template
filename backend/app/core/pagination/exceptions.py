from typing import Any

from app.core.exceptions import ValidationError


class InvalidPaginationError(ValidationError):
    """Raised when pagination parameters are invalid.

    Provides specific context about which pagination parameter failed validation
    and what the valid constraints are.
    """

    def __init__(
        self,
        parameter: str,
        value: Any,
        constraint: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize invalid pagination error.

        Args:
            parameter: The parameter name (limit or offset)
            value: The invalid value provided
            constraint: Description of the validation constraint
            details: Additional error context
            headers: Optional HTTP headers
        """
        message = f"Invalid pagination parameter '{parameter}': value={value!r} violates {constraint}"
        enhanced_details = {
            "parameter": parameter,
            "value": value,
            "constraint": constraint,
            **(details or {}),
        }
        super().__init__(
            message=message,
            details=enhanced_details,
            headers=headers,
        )
