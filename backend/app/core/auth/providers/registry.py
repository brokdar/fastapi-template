"""Provider registry for authentication providers.

This module implements a registry pattern that allows authentication providers
to be registered and discovered at runtime. This enables:
- Feature toggles for enabling/disabling providers via configuration
- Easy addition of new providers without modifying core setup code
- Consistent provider initialization across the application
- Type-safe dependency injection via ProviderDeps dataclasses

Example:
    To add a new provider, create a factory class and register it:

    >>> from app.core.auth.providers.registry import ProviderRegistry
    >>> from app.core.auth.providers.types import ProviderDeps
    >>>
    >>> @dataclass(frozen=True)
    ... class OAuth2Deps(ProviderDeps):
    ...     get_oauth_client: Callable[..., OAuthClient]
    >>>
    >>> @ProviderRegistry.register("oauth2", deps_type=OAuth2Deps)
    ... class OAuth2ProviderFactory:
    ...     name = "oauth2"
    ...     priority = 75
    ...     deps_type = OAuth2Deps
    ...
    ...     @staticmethod
    ...     def create(settings: Settings, deps: OAuth2Deps | None) -> AuthProvider | None:
    ...         if not settings.auth.oauth2.enabled:
    ...             return None
    ...         return OAuth2Provider(get_oauth_client=deps.get_oauth_client)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.auth.providers.base import AuthProvider
    from app.core.auth.providers.types import ProviderDeps


class ProviderFactory(Protocol):
    """Protocol for provider factory classes.

    Provider factories are responsible for creating provider instances
    based on application settings. They check feature flags and return
    None if the provider should not be enabled.

    Attributes:
        name: Unique identifier for the provider.
        priority: Authentication order priority (lower = tried first).
        deps_type: The ProviderDeps subclass required by this provider,
            or None if no dependencies are needed.
    """

    name: str
    priority: int
    deps_type: type[ProviderDeps] | None

    @staticmethod
    def create(settings: Settings, deps: ProviderDeps | None) -> AuthProvider | None:
        """Create a provider instance if enabled.

        Args:
            settings: Application settings containing feature flags and config.
            deps: Typed dependencies for this provider, or None if not required.

        Returns:
            Provider instance if enabled, None if disabled.

        Raises:
            ValueError: If deps is None when required by the provider.
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
        ...     priority = 100
        ...     deps_type = None
        ...
        ...     @staticmethod
        ...     def create(settings: Settings, deps: None) -> AuthProvider | None:
        ...         return JWTAuthProvider(...)
    """

    _factories: dict[str, type[ProviderFactory]] = {}
    _deps_types: dict[str, type[ProviderDeps] | None] = {}
    _provider_order: list[str] = []

    @classmethod
    def register(
        cls,
        name: str,
        *,
        priority: int | None = None,
        deps_type: type[ProviderDeps] | None = None,
    ) -> Callable[[type[ProviderFactory]], type[ProviderFactory]]:
        """Decorator to register a provider factory.

        Args:
            name: Unique name for the provider.
            priority: Optional override for the factory's priority.
                If not provided, uses the factory's class-level priority.
                Lower numbers are tried first during authentication.
            deps_type: The ProviderDeps subclass required by this provider,
                or None if no dependencies are needed.

        Returns:
            Decorator function that registers the factory.

        Raises:
            ValueError: If a provider with the same name is already registered.
        """

        def decorator(factory: type[ProviderFactory]) -> type[ProviderFactory]:
            if name in cls._factories:
                raise ValueError(f"Provider '{name}' is already registered")
            if priority is not None:
                factory.priority = priority
            factory.deps_type = deps_type
            cls._factories[name] = factory
            cls._deps_types[name] = deps_type
            cls._provider_order = sorted(
                [*cls._provider_order, name],
                key=lambda n: cls._factories[n].priority,
            )
            return factory

        return decorator

    @classmethod
    def _validate_dependency_types(
        cls,
        dependencies: dict[str, ProviderDeps],
    ) -> None:
        """Validate provided dependencies are of the correct type.

        Args:
            dependencies: Dict mapping provider name to its deps instance.

        Raises:
            ValueError: If a provided dependency is of the wrong type.
        """
        for name, deps in dependencies.items():
            expected_type = cls._deps_types.get(name)

            if expected_type is None:
                continue

            if not isinstance(deps, expected_type):
                raise ValueError(
                    f"Provider '{name}' requires {expected_type.__name__}, "
                    f"got {type(deps).__name__}"
                )

    @classmethod
    def get_enabled_providers(
        cls,
        settings: Settings,
        dependencies: dict[str, ProviderDeps] | None = None,
    ) -> list[AuthProvider]:
        """Create all enabled providers based on settings.

        Iterates through registered factories in priority order and creates
        provider instances for those that are enabled.

        Args:
            settings: Application settings with feature flags.
            dependencies: Dict mapping provider name to its typed deps instance.

        Returns:
            List of enabled provider instances, sorted by priority.

        Raises:
            ValueError: If a provided dependency is of the wrong type.
        """
        deps = dependencies or {}

        cls._validate_dependency_types(deps)

        providers: list[AuthProvider] = []

        for name in cls._provider_order:
            factory = cls._factories[name]
            provider_deps = deps.get(name)
            provider = factory.create(settings, provider_deps)
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
    def get_required_deps_types(cls) -> dict[str, type[ProviderDeps]]:
        """Get dependency types for all providers that require them.

        Returns:
            Dict mapping provider name to its ProviderDeps subclass.
        """
        return {
            name: deps_type
            for name, deps_type in cls._deps_types.items()
            if deps_type is not None
        }

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
        cls._deps_types.clear()
        cls._provider_order.clear()
