"""Shared fixtures for API Key authentication provider tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request

from app.core.auth.providers.api_key.models import APIKey
from app.core.auth.providers.api_key.provider import APIKeyProvider
from app.core.security.hasher import BCryptAPIKeyService
from app.domains.users.models import User

# Valid test API key format: sk_ + 64 hex chars = 67 total
VALID_TEST_KEY = "sk_0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
VALID_TEST_KEY_PREFIX = "sk_012345678"  # First 12 chars


@pytest.fixture
def api_key_hasher() -> BCryptAPIKeyService:
    """Provide BCrypt API key hasher instance."""
    return BCryptAPIKeyService()


@pytest.fixture
def mock_get_api_key_service() -> Mock:
    """Provide mock get_api_key_service callable for router creation."""
    return Mock()


@pytest.fixture
def api_key_provider(mock_get_api_key_service: Mock) -> APIKeyProvider:
    """Provide APIKeyProvider instance with default settings."""
    return APIKeyProvider(
        get_api_key_service=mock_get_api_key_service,
        header_name="X-API-Key",
    )


@pytest.fixture
def sample_user() -> User:
    """Provide sample User instance for testing."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$KIXqZHpJxV5XnV2Z8ZzJXe",
        is_active=True,
    )


@pytest.fixture
def inactive_user() -> User:
    """Provide inactive User instance for testing."""
    return User(
        id=2,
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password="$2b$12$KIXqZHpJxV5XnV2Z8ZzJXe",
        is_active=False,
    )


@pytest.fixture
def sample_api_key(api_key_hasher: BCryptAPIKeyService) -> tuple[str, APIKey]:
    """Provide sample API key with its model."""
    plaintext, key_hash = api_key_hasher.generate_key()
    prefix = api_key_hasher.extract_prefix(plaintext)

    api_key = APIKey(
        id=1,
        user_id=1,
        key_hash=key_hash,
        key_prefix=prefix,
        name="Test API Key",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        created_at=datetime.now(UTC),
    )
    return plaintext, api_key


@pytest.fixture
def expired_api_key(api_key_hasher: BCryptAPIKeyService) -> tuple[str, APIKey]:
    """Provide expired API key with its model."""
    plaintext, key_hash = api_key_hasher.generate_key()
    prefix = api_key_hasher.extract_prefix(plaintext)

    api_key = APIKey(
        id=2,
        user_id=1,
        key_hash=key_hash,
        key_prefix=prefix,
        name="Expired API Key",
        expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
        created_at=datetime.now(UTC) - timedelta(days=31),
    )
    return plaintext, api_key


@pytest.fixture
def mock_user_service() -> AsyncMock:
    """Provide mocked AuthenticationUserService."""
    return AsyncMock()


@pytest.fixture
def mock_api_key_repository() -> AsyncMock:
    """Provide mocked APIKeyRepository."""
    return AsyncMock()


@pytest.fixture
def mock_request_with_api_key() -> Mock:
    """Provide mocked Request with X-API-Key header."""
    request = Mock(spec=Request)
    request.headers = Mock()
    request.headers.get = Mock(return_value="sk_test_key_value")
    request.state = Mock()
    return request


@pytest.fixture
def mock_request_without_api_key() -> Mock:
    """Provide mocked Request without X-API-Key header."""
    request = Mock(spec=Request)
    request.headers = Mock()
    request.headers.get = Mock(return_value=None)
    return request
