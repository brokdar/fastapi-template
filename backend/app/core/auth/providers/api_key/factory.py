"""API Key provider factory for the provider registry.

This module provides a factory that creates APIKeyProvider instances
based on application settings and feature flags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.auth.providers.api_key.dependencies import APIKeyDeps
from app.core.auth.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.base import AuthProvider
    from app.core.auth.providers.types import ProviderDeps


@ProviderRegistry.register("api_key", deps_type=APIKeyDeps)
class APIKeyProviderFactory:
    """Factory for creating API Key authentication providers.

    Creates APIKeyProvider instances when API Key authentication is enabled.
    API key has a lower priority number (50) so it's tried before JWT (100).
    """

    name = "api_key"
    priority = 50
    deps_type: type[ProviderDeps] | None = APIKeyDeps

    @staticmethod
    def create(settings: Settings, deps: ProviderDeps | None) -> AuthProvider | None:
        """Create API Key provider if enabled in settings.

        Args:
            settings: Application settings containing API Key configuration.
            deps: Typed dependencies containing get_api_key_service callable.

        Returns:
            APIKeyProvider instance if enabled, None if disabled.

        Raises:
            ValueError: If deps is None or wrong type when provider is enabled.
        """
        if not settings.auth.api_key.enabled:
            return None

        if not isinstance(deps, APIKeyDeps):
            raise ValueError(
                "API Key provider requires APIKeyDeps. "
                "This should have been caught by registry validation."
            )

        from app.core.auth.providers.api_key.provider import APIKeyProvider

        return APIKeyProvider(
            get_api_key_service=deps.get_api_key_service,
            header_name=settings.auth.api_key.header_name,
        )
