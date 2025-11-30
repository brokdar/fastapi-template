"""Authentication orchestration service managing multiple providers."""

from collections.abc import Awaitable, Callable, Sequence
from functools import cached_property
from inspect import Parameter, Signature
from typing import Any, cast

import structlog
from fastapi import Depends, FastAPI, Request

from app.core.auth.exceptions import InvalidTokenError
from app.core.auth.providers.base import AuthProvider
from app.core.auth.signature_utils import typed_signature
from app.core.exceptions import AuthorizationError
from app.domains.users.models import User, UserRole
from app.domains.users.services import UserService

logger = structlog.get_logger("auth")

type UserServiceDependency = Callable[..., UserService]


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
        get_user_service: UserServiceDependency,
        providers: Sequence[AuthProvider],
        provider_dependencies: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        """Initialize AuthService with dependency callable and providers.

        Args:
            get_user_service: Callable that returns UserService (dependency).
            providers: List of authentication providers in order of priority.
            provider_dependencies: Optional dict of named dependencies to inject
                into request.state for provider use.
        """
        self.get_user_service: UserServiceDependency = get_user_service
        self._providers: Sequence[AuthProvider] = providers
        self._provider_dependencies: dict[str, Callable[..., Any]] = (
            provider_dependencies or {}
        )

    @cached_property
    def _dependency_signature(self) -> Signature:
        """Generate dynamic signature with security schemes from all providers.

        Creates a function signature that includes Depends(scheme) parameters for
        each provider's security scheme. FastAPI inspects this signature to register
        all security schemes in OpenAPI documentation with OR logic.

        The generated signature includes:
        - request: Request parameter
        - token_{provider_name}: One parameter per provider with Depends(scheme)
        - user_service: UserService dependency

        Parameter names are unique even if multiple providers have the same name
        (e.g., token_jwt, token_jwt_1, token_jwt_2).

        Cached after first access to avoid regenerating on every property/method call.

        Returns:
            Signature with all provider security schemes as dependencies.
        """
        parameters: list[Parameter] = [
            Parameter(
                name="request",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Request,
            )
        ]

        seen_names: set[str] = set()
        for provider in self._providers:
            scheme = provider.get_security_scheme()

            base_name = f"token_{provider.name}"
            param_name = base_name
            counter = 1
            while param_name in seen_names:
                param_name = f"{base_name}_{counter}"
                counter += 1
            seen_names.add(param_name)

            parameters.append(
                Parameter(
                    name=param_name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    default=Depends(cast(Callable[..., Any], scheme)),
                    annotation=str | None,
                )
            )

        parameters.append(
            Parameter(
                name="user_service",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(self.get_user_service),
                annotation=UserService,
            )
        )

        # Add provider dependencies to signature
        for dep_name, dep_callable in self._provider_dependencies.items():
            parameters.append(
                Parameter(
                    name=dep_name,
                    kind=Parameter.POSITIONAL_OR_KEYWORD,
                    default=Depends(dep_callable),
                    annotation=Any,
                )
            )

        return Signature(parameters, return_annotation=User)

    async def _authenticate(self, request: Request, user_service: UserService) -> User:
        """Authenticate request using registered providers.

        Tries each provider in registration order. First provider that can
        authenticate and returns a valid user wins.

        Args:
            request: The incoming HTTP request.
            user_service: Service for user operations.

        Returns:
            Authenticated User object.

        Raises:
            InvalidTokenError: If no provider successfully authenticates.
        """
        for provider in self._providers:
            if provider.can_authenticate(request):
                logger.debug("authentication_attempted", provider=provider.name)
                user: User | None = await provider.authenticate(request, user_service)
                if user:
                    logger.info(
                        "user_authenticated",
                        provider=provider.name,
                        user_id=user.id,
                        username=user.username,
                    )
                    return user

        logger.warning(
            "authentication_failed",
            reason="all_providers_failed",
            providers_tried=[p.name for p in self._providers],
        )
        raise InvalidTokenError("Authentication failed")

    @property
    def require_user(self) -> Callable[..., Awaitable[User]]:
        """FastAPI dependency for requiring authenticated user.

        Generates a dependency with dynamic signature including all provider
        security schemes for OpenAPI documentation. At runtime, ignores the
        token_* parameters and uses the standard multi-provider authentication.

        The generated signature includes Depends(scheme) for each provider,
        allowing FastAPI to register all security schemes in OpenAPI with OR
        logic (user can authenticate with any one provider).

        Returns:
            Dependency function that authenticates and returns the user.

        Raises:
            InvalidTokenError: If authentication fails.
        """
        signature = self._dependency_signature

        @typed_signature(signature)
        async def dependency(
            request: Request,
            user_service: UserService,
            **kwargs: Any,
        ) -> User:
            # Inject provider dependencies into request.state
            for dep_name in self._provider_dependencies:
                if dep_name in kwargs:
                    setattr(request.state, dep_name, kwargs[dep_name])

            user = await self._authenticate(request, user_service)
            request.state.user = user
            return user

        return dependency

    @property
    def has_providers(self) -> bool:
        """Check if any authentication providers are configured.

        Returns:
            True if at least one provider is registered, False otherwise.
        """
        return bool(self._providers)

    def require_roles(self, *roles: UserRole) -> Callable[..., Awaitable[User]]:
        """FastAPI dependency factory for role-based access control.

        Depends on require_user for authentication, then validates the user
        has one of the required roles. Security schemes are inherited from
        require_user dependency for OpenAPI documentation.

        Args:
            *roles: One or more required roles (user must have at least one).

        Returns:
            Dependency function that authenticates user and checks role.

        Raises:
            InvalidTokenError: If authentication fails.
            AuthorizationError: If user doesn't have required role.
        """
        require_user_dep: Callable[..., Awaitable[User]] = self.require_user

        async def dependency(user: User = Depends(require_user_dep)) -> User:
            if user.role not in roles:
                logger.warning(
                    "authorization_failed",
                    reason="insufficient_role",
                    user_id=user.id,
                    user_role=user.role,
                    required_roles=[r.value for r in roles],
                )
                raise AuthorizationError(
                    message=f"User role '{user.role.value}' not authorized. "
                    f"Required roles: {', '.join(r.value for r in roles)}"
                )

            return user

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
            app.include_router(router, prefix="/auth", tags=["auth"])
            logger.debug(
                "provider_router_registered",
                provider=provider.name,
            )
