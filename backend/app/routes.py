from fastapi import FastAPI

from app.dependencies import auth_service
from app.domains.health.endpoints import router as health_router
from app.domains.users.endpoints import router as users_router


def setup_routes(app: FastAPI, prefix: str = "") -> None:
    """Registers all routers with the FastAPI application.

    Includes dynamic registration of authentication provider routes.

    Args:
        app: Application to add the routers to.
        prefix: Optional prefix for all routes. Defaults to "".
    """
    auth_service.register_routes(app)
    app.include_router(health_router, prefix=prefix)
    app.include_router(users_router, prefix=prefix)
