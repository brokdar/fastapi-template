"""JWT provider factory for the provider registry.

This module provides a factory that creates JWTAuthProvider instances
based on application settings and feature flags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.auth.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.base import AuthProvider
    from app.core.auth.providers.types import ProviderDeps


@ProviderRegistry.register("jwt")
class JWTProviderFactory:
    """Factory for creating JWT authentication providers.

    Creates JWTAuthProvider instances when JWT authentication is enabled.
    JWT has a higher priority number (100) so it's tried after API key (50).
    Optionally creates a token blacklist store if blacklist is enabled.
    """

    name = "jwt"
    priority = 100
    deps_type: type[ProviderDeps] | None = None

    @staticmethod
    def create(settings: Settings, deps: ProviderDeps | None) -> AuthProvider | None:
        """Create JWT provider if enabled in settings.

        Creates a blacklist store if blacklist is enabled in settings.
        The store type (Redis or in-memory) is determined by the
        blacklist_redis_url setting.

        Args:
            settings: Application settings containing JWT configuration.
            deps: Not used - JWT provider has no external dependencies.

        Returns:
            JWTAuthProvider instance if enabled, None if disabled.
        """
        if not settings.auth.jwt.enabled:
            return None

        from app.core.auth.providers.jwt.provider import JWTAuthProvider

        blacklist_store = None
        if settings.auth.jwt.blacklist_enabled:
            from app.core.auth.providers.jwt.blacklist import create_blacklist_store

            blacklist_store = create_blacklist_store(
                redis_url=settings.auth.jwt.blacklist_redis_url
            )

        return JWTAuthProvider(settings.auth.jwt, blacklist_store)
