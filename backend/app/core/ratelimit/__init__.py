"""Rate limiting module for FastAPI endpoints.

Provides a shared rate limiter instance and key functions for applying
rate limits to routes. Supports both IP-based and user-based rate limiting.

Example:
    from app.core.ratelimit import limiter, get_user_identifier

    @router.get("/public")
    @limiter.limit("100/minute")
    async def public_endpoint(request: Request): ...

    @router.post("/private")
    @limiter.limit("10/minute", key_func=get_user_identifier)
    async def private_endpoint(request: Request, user: User = Depends(...)): ...
"""

from app.core.ratelimit.limiter import get_user_identifier, limiter, setup_rate_limiter

__all__ = ["limiter", "get_user_identifier", "setup_rate_limiter"]
