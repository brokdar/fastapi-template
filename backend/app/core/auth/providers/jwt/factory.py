"""JWT provider factory for the provider registry.

This module provides a factory that creates JWTAuthProvider instances
based on application settings and feature flags.
"""

from typing import TYPE_CHECKING, Any

from app.core.auth.providers.registry import ProviderRegistry

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.jwt.provider import JWTAuthProvider


@ProviderRegistry.register("jwt", priority=100)
class JWTProviderFactory:
    """Factory for creating JWT authentication providers.

    Creates JWTAuthProvider instances when JWT authentication is enabled.
    JWT has a higher priority number (100) so it's tried after API key (50).
    """

    name = "jwt"

    @staticmethod
    def create(settings: "Settings", **deps: Any) -> "JWTAuthProvider | None":
        """Create JWT provider if enabled in settings.

        Args:
            settings: Application settings containing JWT configuration.
            **deps: Additional dependencies (not used by JWT provider).

        Returns:
            JWTAuthProvider instance if enabled, None if disabled.
        """
        if not settings.features.auth.jwt_enabled:
            return None

        # Import here to avoid circular imports
        from app.core.auth.providers.jwt.provider import JWTAuthProvider

        return JWTAuthProvider(
            secret_key=settings.auth.jwt.secret_key.get_secret_value(),
            algorithm=settings.auth.jwt.algorithm,
            access_token_expire_minutes=settings.auth.jwt.access_token_expire_minutes,
            refresh_token_expire_days=settings.auth.jwt.refresh_token_expire_days,
        )
