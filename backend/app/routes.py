"""Route registration for the FastAPI application.

Authentication routes are registered by setup_authentication() in main.py.
This module handles the registration of domain routes.

Note: Domain router imports are done lazily inside setup_routes() to ensure
auth_service is populated before any endpoints that depend on it are loaded.
"""

from fastapi import FastAPI


def setup_routes(app: FastAPI, *, auth_enabled: bool = True, prefix: str = "") -> None:
    """Register domain routers with the FastAPI application.

    Note: Authentication provider routes (login, refresh, api-keys) are
    registered separately by setup_authentication() in main.py.

    Domain imports are done lazily here to ensure auth_service is populated
    before endpoint modules that depend on it are loaded.

    Args:
        app: Application to add the routers to.
        auth_enabled: Whether authentication is enabled. When False,
            user management routes are not registered.
        prefix: Optional prefix for all routes. Defaults to "".
    """
    # Health routes are always available (no auth dependency)
    from app.domains.health.endpoints import router as health_router

    app.include_router(health_router, prefix=prefix)

    # User routes require authentication - only import/register if auth enabled
    if auth_enabled:
        from app.domains.users.endpoints import router as users_router

        app.include_router(users_router, prefix=prefix)
