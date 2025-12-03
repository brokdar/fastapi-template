"""Shared rate limiter instance and key functions.

This module provides a reusable rate limiter that can be applied to any route
in the application. It includes both IP-based and user-based key functions
for different rate limiting strategies.

Example usage:
    from app.core.ratelimit import limiter, get_user_identifier

    # IP-based rate limiting (default)
    @router.get("/endpoint")
    @limiter.limit("10/minute")
    async def endpoint(request: Request): ...

    # User-based rate limiting
    @router.post("/user-action")
    @limiter.limit("5/minute", key_func=get_user_identifier)
    async def user_action(request: Request, user: User = Security(...)): ...
"""

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Shared limiter instance - reusable across any route
# Uses IP address as the default key function
limiter = Limiter(key_func=get_remote_address)


def get_user_identifier(request: Request) -> str:
    """Extract user identifier from request for user-based rate limiting.

    This key function extracts the user ID from request.state.user, which is
    set by the authentication system. Falls back to IP address if no user
    is authenticated (shouldn't happen for protected routes).

    Args:
        request: FastAPI request object with potential user in state.

    Returns:
        User identifier string in format "user:{id}" or IP address as fallback.
    """
    user = getattr(request.state, "user", None)
    if user:
        return f"user:{user.id}"
    return get_remote_address(request)


def setup_rate_limiter(app: FastAPI) -> None:
    """Configure rate limiting for the application.

    Attaches the shared limiter instance to app.state and registers
    the exception handler for rate limit exceeded responses.

    Args:
        app: FastAPI application instance.
    """
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
