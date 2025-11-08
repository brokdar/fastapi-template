from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.domains.users.models import User, UserRole
from app.main import app


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return a mocked AsyncSession for testing database operations."""
    mock = AsyncMock(spec=AsyncSession)
    mock.exec.return_value = MagicMock()
    return mock


@pytest.fixture(scope="session")
def api_prefix() -> str:
    """Return the API prefix."""
    return get_settings().API_PATH


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Return a test client with no authentication."""
    return TestClient(app)


@pytest.fixture(scope="session")
def create_user() -> Callable[..., User]:
    """Factory function to create User instances with custom data."""

    def _create_user(**kwargs: Any) -> User:
        defaults = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": UserRole.USER,
            "is_active": True,
            "hashed_password": "hashed_password_123",
        }
        defaults.update(kwargs)
        return User(**defaults)

    return _create_user


@pytest.fixture
def regular_user(create_user: Callable[..., User]) -> User:
    """Provide sample user data for testing."""
    return create_user()


@pytest.fixture
def admin_user(create_user: Callable[..., User]) -> User:
    """Provide admin user data for testing."""
    return create_user(
        id=2,
        username="admin_user",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
    )
