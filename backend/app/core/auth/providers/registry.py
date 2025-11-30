"""Provider registry for authentication providers.

This module implements a registry pattern that allows authentication providers
to be registered and discovered at runtime. This enables:
- Feature toggles for enabling/disabling providers via configuration
- Easy addition of new providers without modifying core setup code
- Consistent provider initialization across the application

Example:
    To add a new provider, create a factory class and register it:

    >>> from app.core.auth.providers.registry import ProviderRegistry
    >>>
    >>> @ProviderRegistry.register("oauth2")
    ... class OAuth2ProviderFactory:
    ...     name = "oauth2"
    ...
    ...     @staticmethod
    ...     def create(settings: Settings, **deps: Any) -> OAuth2Provider | None:
    ...         if not getattr(settings.features.auth, "oauth2_enabled", False):
    ...             return None
    ...         return OAuth2Provider(...)
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.base import AuthProvider


class ProviderFactory(Protocol):
    """Protocol for provider factory classes.

    Provider factories are responsible for creating provider instances
    based on application settings. They check feature flags and return
    None if the provider should not be enabled.

    Attributes:
        name: Unique identifier for the provider.
    """

    name: str

    @staticmethod
    def create(settings: "Settings", **dependencies: Any) -> "AuthProvider | None":
        """Create a provider instance if enabled.

        Args:
            settings: Application settings containing feature flags and config.
            **dependencies: Additional dependencies required by the provider
                (e.g., get_api_key_service callable).

        Returns:
            Provider instance if enabled, None if disabled.

        Raises:
            ValueError: If required dependencies are missing.
        """
        ...


class ProviderRegistry:
    """Registry for authentication provider factories.

    This class maintains a registry of provider factories that can be used
    to create provider instances based on configuration. Providers are
    registered using the @ProviderRegistry.register decorator.

    Example:
        >>> @ProviderRegistry.register("jwt")
        ... class JWTProviderFactory:
        ...     name = "jwt"
        ...     @staticmethod
        ...     def create(settings, **deps):
        ...         return JWTAuthProvider(...)
    """

    _factories: dict[str, type[ProviderFactory]] = {}
    _provider_order: list[str] = []

    @classmethod
    def register(
        cls,
        name: str,
        *,
        priority: int = 100,
    ) -> Callable[[type[ProviderFactory]], type[ProviderFactory]]:
        """Decorator to register a provider factory.

        Args:
            name: Unique name for the provider.
            priority: Lower numbers are tried first during authentication.
                Default is 100. API key is typically 50, JWT is 100.

        Returns:
            Decorator function that registers the factory.

        Raises:
            ValueError: If a provider with the same name is already registered.
        """

        def decorator(factory: type[ProviderFactory]) -> type[ProviderFactory]:
            if name in cls._factories:
                raise ValueError(f"Provider '{name}' is already registered")
            cls._factories[name] = factory
            # Insert in sorted order by priority
            cls._provider_order = sorted(
                [*cls._provider_order, name],
                key=lambda n: getattr(cls._factories[n], "priority", priority),
            )
            # Store priority on the factory for future reference
            factory.priority = priority  # type: ignore[attr-defined]
            return factory

        return decorator

    @classmethod
    def get_enabled_providers(
        cls,
        settings: "Settings",
        **dependencies: Any,
    ) -> list["AuthProvider"]:
        """Create all enabled providers based on settings.

        Iterates through registered factories in priority order and creates
        provider instances for those that are enabled.

        Args:
            settings: Application settings with feature flags.
            **dependencies: Dependencies to pass to provider factories.

        Returns:
            List of enabled provider instances, sorted by priority.
        """
        providers: list[AuthProvider] = []

        for name in cls._provider_order:
            factory = cls._factories[name]
            provider = factory.create(settings, **dependencies)
            if provider is not None:
                providers.append(provider)

        return providers

    @classmethod
    def get_factory(cls, name: str) -> type[ProviderFactory] | None:
        """Get a specific factory by name.

        Args:
            name: The provider name.

        Returns:
            The factory class if found, None otherwise.
        """
        return cls._factories.get(name)

    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered provider names in priority order.

        Returns:
            List of provider names.
        """
        return list(cls._provider_order)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers (useful for testing)."""
        cls._factories.clear()
        cls._provider_order.clear()
