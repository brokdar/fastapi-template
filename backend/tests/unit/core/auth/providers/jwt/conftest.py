"""Shared fixtures for JWT authentication provider tests."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock

import jwt
import pytest
from fastapi import Request
from pydantic import SecretStr

from app.core.auth.providers.jwt.config import JWTSettings
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.domains.users.models import User


@pytest.fixture
def test_jwt_settings() -> JWTSettings:
    """Provide test JWTSettings instance for provider and router creation.

    Uses very high rate limits to avoid rate limiting affecting tests.
    """
    return JWTSettings(
        secret_key=SecretStr("test_secret_key_with_minimum_32_characters_required"),
        login_rate_limit="1000/minute",
        refresh_rate_limit="1000/minute",
    )


@pytest.fixture
def secret_key(test_jwt_settings: JWTSettings) -> str:
    """Provide valid secret key for JWT operations."""
    return test_jwt_settings.secret_key.get_secret_value()


@pytest.fixture
def jwt_provider(test_jwt_settings: JWTSettings) -> JWTAuthProvider:
    """Provide JWTAuthProvider instance with default settings."""
    return JWTAuthProvider(test_jwt_settings)


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
def mock_user_service() -> AsyncMock:
    """Provide mocked AuthenticationUserService."""
    service = AsyncMock()
    service.parse_id = Mock(side_effect=lambda x: int(x))
    return service


@pytest.fixture
def mock_request_with_bearer_token() -> Mock:
    """Provide mocked Request with valid Bearer token."""
    request = Mock(spec=Request)
    request.headers.get.return_value = "Bearer valid_token_string"
    return request


@pytest.fixture
def mock_request_without_token() -> Mock:
    """Provide mocked Request without Authorization header."""
    request = Mock(spec=Request)
    request.headers.get.return_value = ""
    return request


@pytest.fixture
def valid_access_token(jwt_provider: JWTAuthProvider) -> str:
    """Provide valid access token for testing."""
    return jwt_provider.create_access_token("1")


@pytest.fixture
def valid_refresh_token(jwt_provider: JWTAuthProvider) -> str:
    """Provide valid refresh token for testing."""
    return jwt_provider.create_refresh_token("1")


@pytest.fixture
def expired_token(secret_key: str) -> str:
    """Provide expired JWT token for testing."""
    now = datetime.now(UTC)
    expired_time = now - timedelta(hours=1)

    payload: dict[str, Any] = {
        "sub": "1",
        "exp": int(expired_time.timestamp()),
        "iat": int((expired_time - timedelta(minutes=15)).timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")


@pytest.fixture
def malformed_token() -> str:
    """Provide malformed JWT token for testing."""
    return "not.a.valid.jwt.token"


@pytest.fixture
def token_with_invalid_signature(secret_key: str) -> str:
    """Provide JWT token with invalid signature."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=15)

    payload: dict[str, Any] = {
        "sub": "1",
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, "wrong_secret_key", algorithm="HS256")
