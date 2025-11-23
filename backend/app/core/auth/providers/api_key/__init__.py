"""API Key authentication provider.

This module provides API key-based authentication for the FastAPI application.
"""

from app.core.security.hasher import (
    APIKeyHasher,
    BCryptAPIKeyService,
    default_api_key_service,
)

from .exceptions import (
    APIKeyExpiredError,
    APIKeyLimitExceededError,
    APIKeyNotFoundError,
    InvalidAPIKeyError,
)
from .models import APIKey
from .provider import APIKeyProvider
from .schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from .services import APIKeyService

__all__: list[str] = [
    # Provider
    "APIKeyProvider",
    # Model
    "APIKey",
    # Service
    "APIKeyService",
    # Security
    "APIKeyHasher",
    "BCryptAPIKeyService",
    "default_api_key_service",
    # Schemas
    "APIKeyCreate",
    "APIKeyCreateResponse",
    "APIKeyResponse",
    "APIKeyListResponse",
    # Exceptions
    "APIKeyNotFoundError",
    "APIKeyLimitExceededError",
    "APIKeyExpiredError",
    "InvalidAPIKeyError",
]
