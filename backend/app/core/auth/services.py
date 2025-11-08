"""Authentication orchestration service managing multiple providers."""

from collections.abc import Awaitable, Callable, Sequence

import structlog
from fastapi import Depends, FastAPI, Request

from app.core.auth.exceptions import InvalidTokenError
from app.core.auth.providers.base import AuthProvider
from app.core.exceptions import AuthorizationError
from app.domains.users.models import User, UserRole
from app.domains.users.repositories import UserRepository

logger = structlog.get_logger("auth")

type UserRepositoryDependency = Callable[..., UserRepository]


class AuthService:
    """Manages authentication for a FastAPI application.

    Coordinates multiple authentication providers and provides FastAPI
    dependencies for route protection and role-based access control.

    Providers are tried in the order they are registered. The first provider
    where can_authenticate() returns True will be used for authentication.

    Uses the dependency callable pattern: stores a callable for user repository
    which FastAPI resolves per-request, ensuring fresh database sessions.
    """

    def __init__(
        self,
        get_user_repository: UserRepositoryDependency,
        providers: Sequence[AuthProvider],
    ) -> None:
        """Initialize AuthService with dependency callable and providers.

        Args:
            get_user_repository: Callable that returns UserRepository (dependency).
            providers: List of authentication providers in order of priority.
        """
        self.get_user_repository = get_user_repository
        self._providers = providers

    @property
    def require_user(self) -> Callable[..., Awaitable[User]]:
        """FastAPI dependency for requiring authenticated user.

        Returns a dependency function that injects UserRepository per-request
        and authenticates the user using registered providers.

        Use this as a dependency in route handlers to protect endpoints.

        Example:
            @app.get("/protected")
            async def protected_route(user: User = Depends(auth_service.require_user)):
                return {"user_id": user.id}

        Returns:
            Dependency function that authenticates and returns the user.

        Raises:
            InvalidTokenError: If authentication fails.
        """

        async def dependency(
            request: Request,
            user_repository: UserRepository = Depends(self.get_user_repository),
        ) -> User:
            for provider in self._providers:
                if not provider.can_authenticate(request):
                    logger.debug(
                        "Provider cannot authenticate request",
                        provider=provider.name,
                    )
                    continue

                logger.debug(
                    "Attempting authentication",
                    provider=provider.name,
                )

                if user := await provider.authenticate(request, user_repository):
                    logger.info(
                        "User authenticated successfully",
                        provider=provider.name,
                        user_id=user.id,
                        username=user.username,
                    )
                    return user

            logger.warning(
                "Authentication failed for all providers",
                providers_tried=[p.name for p in self._providers],
            )
            raise InvalidTokenError("Authentication failed")

        return dependency

    def require_roles(self, *roles: UserRole) -> Callable[..., Awaitable[User]]:
        """FastAPI dependency factory for role-based access control.

        Creates a dependency that requires the user to have one of the
        specified roles. Injects UserRepository per-request and performs
        authentication before checking roles.

        Args:
            *roles: One or more required roles (user must have at least one).

        Returns:
            Dependency function that authenticates user and checks role.

        Raises:
            InvalidTokenError: If authentication fails.
            AuthorizationError: If user doesn't have required role.

        Example:
            @app.get("/admin")
            async def admin_only(
                user: User = Depends(auth_service.require_roles(UserRole.ADMIN))
            ):
                return {"admin": user.username}
        """

        async def dependency(
            request: Request,
            user_repository: UserRepository = Depends(self.get_user_repository),
        ) -> User:
            # Authenticate user (same logic as require_user)
            authenticated_user: User | None = None
            for provider in self._providers:
                if not provider.can_authenticate(request):
                    logger.debug(
                        "Provider cannot authenticate request",
                        provider=provider.name,
                    )
                    continue

                logger.debug(
                    "Attempting authentication",
                    provider=provider.name,
                )

                if user := await provider.authenticate(request, user_repository):
                    logger.info(
                        "User authenticated successfully",
                        provider=provider.name,
                        user_id=user.id,
                        username=user.username,
                    )
                    authenticated_user = user
                    break

            if not authenticated_user:
                logger.warning(
                    "Authentication failed for all providers",
                    providers_tried=[p.name for p in self._providers],
                )
                raise InvalidTokenError("Authentication failed")

            # Check role authorization
            if authenticated_user.role not in roles:
                logger.warning(
                    "User lacks required role",
                    user_id=authenticated_user.id,
                    user_role=authenticated_user.role,
                    required_roles=[r.value for r in roles],
                )
                raise AuthorizationError(
                    message=f"User role '{authenticated_user.role.value}' not authorized. "
                    f"Required roles: {', '.join(r.value for r in roles)}"
                )

            return authenticated_user

        return dependency

    def register_routes(self, app: FastAPI) -> None:
        """Register provider's authentication routes.

        Mounts the provider's router (login, logout, etc.) under
        the configured prefix.

        Args:
            app: FastAPI application instance
        """
        for provider in self._providers:
            router = provider.get_router()
            app.include_router(router, prefix="auth", tags=["auth"])
            logger.debug(
                "Provider router registered",
                provider=provider.name,
            )
