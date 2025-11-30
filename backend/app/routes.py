"""Route registration for the FastAPI application.

Authentication routes are registered via setup_authentication() in main.py.
This module handles non-auth domain routes only.
"""

from fastapi import FastAPI

from app.domains.health.endpoints import router as health_router


def setup_routes(app: FastAPI, *, prefix: str = "") -> None:
    """Register non-auth domain routers with the FastAPI application.

    Auth-related routes (login, users, api-keys) are registered separately
    by setup_authentication().

    Args:
        app: Application to add the routers to.
        prefix: Optional prefix for all routes. Defaults to "".
    """
    app.include_router(health_router, prefix=prefix)
