from fastapi import FastAPI

from app.core.auth.endpoints import router as auth_router
from app.domains.health.endpoints import router as health_router
from app.domains.users.endpoints import router as users_router


def setup_routes(app: FastAPI, prefix: str = "") -> None:
    """Registers all routers with the FastAPI application.

    Args:
        app (FastAPI): Application to add the routers to.
        prefix (str, optional): Optional prefix for all routes. Defaults to "".
    """
    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
