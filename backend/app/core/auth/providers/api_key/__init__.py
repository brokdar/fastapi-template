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
    InvalidAPIKeyIDError,
)
from .models import APIKey, APIKeyID, parse_api_key_id
from .provider import APIKeyProvider
from .repositories import APIKeyRepository
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
    # Model and Types
    "APIKey",
    "APIKeyID",
    "parse_api_key_id",
    # Repository
    "APIKeyRepository",
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
    "InvalidAPIKeyIDError",
]
