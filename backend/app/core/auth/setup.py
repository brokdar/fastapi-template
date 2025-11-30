"""Authentication setup module.

This module provides the main entry point for configuring authentication
in a FastAPI application. It replaces manual provider wiring with a
single function call.

Example:
    >>> from app.core.auth.setup import setup_authentication
    >>> from app import dependencies
    >>>
    >>> auth_result = setup_authentication(
    ...     app=app,
    ...     settings=settings,
    ...     get_user_service=dependencies.get_user_service,
    ...     get_api_key_service=dependencies.get_api_key_service,
    ... )
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import FastAPI

from app.core.auth.providers import ProviderRegistry
from app.core.auth.services import AuthService

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.api_key.services import APIKeyService
    from app.core.auth.providers.base import AuthProvider
    from app.domains.users.services import UserService

logger = structlog.get_logger("auth.setup")


@dataclass
class AuthenticationResult:
    """Result of authentication setup.

    Contains references to the created auth service and providers for
    dependency injection and testing.

    Attributes:
        auth_service: The configured AuthService instance.
        providers: List of enabled provider instances.
        enabled_provider_names: Names of enabled providers for logging.
    """

    auth_service: AuthService
    providers: list["AuthProvider"] = field(default_factory=list)
    enabled_provider_names: list[str] = field(default_factory=list)


def setup_authentication(
    app: FastAPI,
    settings: "Settings",
    get_user_service: Callable[..., "UserService"],
    get_api_key_service: Callable[..., "APIKeyService"] | None = None,
) -> AuthenticationResult | None:
    """Initialize authentication system based on settings.

    This is the main entry point for authentication configuration. It:
    1. Checks feature flags to determine if auth should be enabled
    2. Creates enabled providers via the ProviderRegistry
    3. Creates and configures the AuthService
    4. Registers authentication routes on the app
    5. Populates dependencies.auth_service for backward compatibility

    Args:
        app: FastAPI application instance.
        settings: Application settings containing feature flags and auth config.
        get_user_service: Dependency factory that returns UserService.
        get_api_key_service: Dependency factory for APIKeyService (required if
            API key auth is enabled).

    Returns:
        AuthenticationResult if auth is enabled, None if disabled.

    Raises:
        ValueError: If auth is enabled but no providers are configured,
            or if API key auth is enabled but get_api_key_service is not provided.

    Example:
        >>> # Basic setup with all features enabled (default)
        >>> auth_result = setup_authentication(
        ...     app=app,
        ...     settings=settings,
        ...     get_user_service=dependencies.get_user_service,
        ...     get_api_key_service=dependencies.get_api_key_service,
        ... )
        >>>
        >>> # JWT-only setup (disable API key in settings)
        >>> # Set FEATURES__AUTH__API_KEY_ENABLED=false in environment
        >>> auth_result = setup_authentication(
        ...     app=app,
        ...     settings=settings,
        ...     get_user_service=dependencies.get_user_service,
        ... )
    """
    # Check master auth switch
    if not settings.features.auth.enabled:
        logger.info("auth_disabled", reason="FEATURES__AUTH__ENABLED=false")
        return None

    # Build dependencies dict for provider factories
    factory_deps: dict[str, Any] = {}
    if get_api_key_service is not None:
        factory_deps["get_api_key_service"] = get_api_key_service

    # Create enabled providers via registry
    providers = ProviderRegistry.get_enabled_providers(settings, **factory_deps)

    if not providers:
        raise ValueError(
            "Authentication is enabled but no providers are configured. "
            "Enable at least one provider via FEATURES__AUTH__JWT_ENABLED=true "
            "or FEATURES__AUTH__API_KEY_ENABLED=true"
        )

    enabled_names = [p.name for p in providers]
    logger.info("auth_providers_enabled", providers=enabled_names)

    # Build provider dependencies for request.state injection
    provider_dependencies: dict[str, Callable[..., Any]] = {}
    if get_api_key_service is not None and settings.features.auth.api_key_enabled:
        provider_dependencies["api_key_service"] = get_api_key_service

    # Create AuthService
    auth_service = AuthService(
        get_user_service=get_user_service,
        providers=providers,
        provider_dependencies=provider_dependencies,
    )

    # Populate dependencies.auth_service BEFORE registering routes
    # This is critical because route modules import auth_service from dependencies
    # and use it in Security() decorators
    from app import dependencies

    dependencies.auth_service = auth_service

    # Register authentication routes (after auth_service is available in dependencies)
    auth_service.register_routes(app)
    logger.info("auth_routes_registered")

    return AuthenticationResult(
        auth_service=auth_service,
        providers=providers,
        enabled_provider_names=enabled_names,
    )
