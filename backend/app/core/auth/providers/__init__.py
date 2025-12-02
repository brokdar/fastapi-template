"""Authentication provider implementations.

This module exports the provider registry and base protocol for creating
and managing authentication providers.

Importing this module automatically registers the built-in providers
(JWT and API Key) with the ProviderRegistry.
"""

# Import factories to register them with the registry
# These imports have side effects (registration via decorator)
from app.core.auth.providers.api_key import factory as _api_key_factory  # noqa: F401
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.jwt import factory as _jwt_factory  # noqa: F401
from app.core.auth.providers.registry import ProviderFactory, ProviderRegistry

__all__ = [
    "AuthProvider",
    "ProviderFactory",
    "ProviderRegistry",
]
