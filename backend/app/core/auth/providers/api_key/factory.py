"""API Key provider factory for the provider registry.

This module provides a factory that creates APIKeyProvider instances
based on application settings and feature flags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.auth.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.base import AuthProvider


@ProviderRegistry.register("api_key")
class APIKeyProviderFactory:
    """Factory for creating API Key authentication providers.

    Creates APIKeyProvider instances when API Key authentication is enabled.
    API key has a lower priority number (50) so it's tried before JWT (100).
    """

    name = "api_key"
    priority = 50

    @staticmethod
    def create(settings: Settings, **deps: Any) -> AuthProvider | None:
        """Create API Key provider if enabled in settings.

        Args:
            settings: Application settings containing API Key configuration.
            **deps: Additional dependencies. Must include:
                - get_api_key_service: Callable that returns APIKeyService.

        Returns:
            APIKeyProvider instance if enabled, None if disabled.

        Raises:
            ValueError: If get_api_key_service dependency is missing.
        """
        if not settings.auth.api_key.enabled:
            return None

        get_api_key_service = deps.get("get_api_key_service")
        if get_api_key_service is None:
            raise ValueError(
                "API Key provider requires 'get_api_key_service' dependency. "
                "Pass it to setup_authentication()."
            )

        from app.core.auth.providers.api_key.provider import APIKeyProvider

        return APIKeyProvider(
            get_api_key_service=get_api_key_service,
            header_name=settings.auth.api_key.header_name,
        )
