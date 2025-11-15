"""FastAPI middleware for request tracking and logging."""

import fnmatch
import secrets
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .constants import LoggingConstants


def _calculate_duration_ms(start_time: float) -> float:
    """Calculate request duration in milliseconds.

    Args:
        start_time: The start time from time.time()

    Returns:
        Duration in milliseconds rounded to 2 decimal places
    """
    return round((time.time() - start_time) * 1000, 2)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for request tracking and structured logging.

    Features:
    - Generates unique request IDs for each request
    - Adds request ID to response headers for client tracking
    - Logs request details (method, path, status, duration)
    - Includes user information in response logs when available
    - Supports route exclusion with exact paths and wildcard patterns
    - Uses structlog for structured logging with consistent format

    Exclusion Patterns:
    - Exact paths: "/health", "/ping"
    - Wildcard suffix: "*/health" (matches "/api/health", "/v1/health")
    - Wildcard prefix: "/api/*" (matches "/api/users", "/api/posts")
    - Complex patterns: "/api/*/health" (matches "/api/v1/health", "/api/v2/health")
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        excluded_routes: list[str] | None = None,
        request_id_header: str = "X-Request-ID",
        logger_name: str = "request",
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application
            excluded_routes: List of route paths to exclude from logging.
                            Supports exact paths (e.g., "/health") and wildcard patterns
                            (e.g., "*/health", "/api/*", "/api/*/metrics")
            request_id_header: Header name for the request ID
            logger_name: Name for the structured logger
        """
        super().__init__(app)
        routes = (
            excluded_routes
            if excluded_routes is not None
            else LoggingConstants.COMMON_EXCLUDED_ROUTES
        )

        self.excluded_exact_routes: set[str] = set()
        self.excluded_patterns: list[str] = []

        for route in routes:
            if "*" in route or "?" in route or "[" in route:
                self.excluded_patterns.append(route)
            else:
                self.excluded_exact_routes.add(route)

        self.request_id_header = request_id_header
        self.logger = structlog.get_logger(logger_name)

    def _generate_request_id(self) -> str:
        """Generate a unique request ID.

        Returns:
            A unique request ID string
        """
        token = secrets.token_hex(LoggingConstants.REQUEST_ID_LENGTH // 2)
        return f"{LoggingConstants.REQUEST_ID_PREFIX}{token}"

    def _should_log_request(self, path: str) -> bool:
        """Check if the request should be logged.

        Args:
            path: The request path

        Returns:
            True if the request should be logged, False otherwise
        """
        if path in self.excluded_exact_routes:
            return False

        for pattern in self.excluded_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False

        return True

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and add logging.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            The response from the application
        """
        request_id = self._generate_request_id()
        request.state.request_id = request_id

        log = self.logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None,
        )

        if not self._should_log_request(request.url.path):
            response = await call_next(request)
            response.headers[self.request_id_header] = request_id
            return response

        start_time = time.time()
        log.info("Request started")

        try:
            response = await call_next(request)
            log_data: dict[str, Any] = {
                "status_code": response.status_code,
                "duration_ms": _calculate_duration_ms(start_time),
            }

            user = getattr(request.state, "user", None)
            if user:
                log_data.update(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "user_role": user.role.value,
                    }
                )

            log.info("Request completed", **log_data)

        except Exception as exc:
            error_log_data: dict[str, Any] = {
                "error": str(exc),
                "error_type": type(exc).__name__,
                "duration_ms": _calculate_duration_ms(start_time),
            }

            user = getattr(request.state, "user", None)
            if user:
                error_log_data.update(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "user_role": user.role.value,
                    }
                )

            log.error("Request failed", **error_log_data)
            raise

        response.headers[self.request_id_header] = request_id
        return response
