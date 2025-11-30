"""Authentication setup module.

This module provides functions for creating and configuring authentication
in a FastAPI application.

Example:
    >>> from app.core.auth.setup import create_auth_service, setup_authentication
    >>> from app import dependencies
    >>>
    >>> # In dependencies.py - create the service
    >>> auth_service = create_auth_service(settings, get_user_service, get_api_key_service)
    >>>
    >>> # In main.py - setup routes
    >>> setup_authentication(app, dependencies.auth_service)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import FastAPI

from app.core.auth.providers import ProviderRegistry
from app.core.auth.services import AuthService

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.api_key.services import APIKeyService
    from app.domains.users.services import UserService

logger = structlog.get_logger("auth.setup")


def create_auth_service(
    settings: Settings,
    get_user_service: Callable[..., UserService],
    get_api_key_service: Callable[..., APIKeyService] | None = None,
) -> AuthService:
    """Create AuthService instance based on settings.

    Args:
        settings: Application settings containing feature flags and auth config.
        get_user_service: Dependency factory that returns UserService.
        get_api_key_service: Dependency factory for APIKeyService (required if
            API key auth is enabled).

    Returns:
        Configured AuthService with providers if auth is enabled,
        or AuthService with no providers if disabled (Null Object pattern).

    Raises:
        ValueError: If auth is enabled but no providers are configured.
    """
    if not settings.features.auth.enabled:
        logger.info("auth_disabled", reason="FEATURES__AUTH__ENABLED=false")
        return AuthService(get_user_service=get_user_service, providers=[])

    factory_deps: dict[str, Any] = {}
    if get_api_key_service is not None:
        factory_deps["get_api_key_service"] = get_api_key_service

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

    return AuthService(
        get_user_service=get_user_service,
        providers=providers,
        provider_dependencies=provider_dependencies,
    )


def setup_authentication(
    app: FastAPI,
    auth_service: AuthService,
    *,
    prefix: str = "",
) -> None:
    """Set up authentication for the application.

    Registers all authentication-related routes:
    - Auth provider routes (login, token refresh, api-keys)
    - User management routes (CRUD operations)

    If auth_service has no providers (auth disabled), does nothing.

    Args:
        app: FastAPI application instance.
        auth_service: The AuthService instance.
        prefix: Optional prefix for user management routes.
    """
    auth_service.register_routes(app)

    if not auth_service.has_providers:
        logger.info("auth_setup_skipped", reason="no providers configured")
        return

    from app.domains.users.endpoints import router as users_router

    app.include_router(users_router, prefix=prefix)

    logger.info("auth_setup_complete")
