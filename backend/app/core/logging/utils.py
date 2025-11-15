"""Utility functions for structured logging."""

import structlog
from fastapi import Request


def get_request_id(request: Request) -> str | None:
    """Get the request ID from the request state.

    Args:
        request: The FastAPI request object

    Returns:
        The request ID if available, None otherwise
    """
    return getattr(request.state, "request_id", None)


def get_request_logger(
    request: Request, logger_name: str = "app"
) -> structlog.BoundLogger:
    """Get a logger bound with request context.

    This function creates a logger that automatically includes the request ID
    in all log messages, making it easy to trace requests through the application.

    Args:
        request: The FastAPI request object
        logger_name: Base logger name

    Returns:
        A structlog logger bound with request context

    Example:
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, request: Request):
            log = get_request_logger(request, "users")
            log = log.bind(user_id=user_id, operation="fetch_user")

            log.info("Fetching user")
            # ... business logic ...
            log.info("User fetched successfully")

            return user_data
    """
    logger: structlog.BoundLogger = structlog.get_logger(logger_name)

    request_id = get_request_id(request)
    if request_id:
        logger = logger.bind(request_id=request_id)

    return logger
