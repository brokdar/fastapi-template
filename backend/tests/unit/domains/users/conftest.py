"""Shared fixtures for user domain tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.security.password import PasswordHasher
from app.domains.users.models import User, UserRole
from app.domains.users.repositories import UserRepository
from app.domains.users.schemas import UserCreate
from app.domains.users.services import UserService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provide a mocked UserRepository for service testing."""
    mock = AsyncMock(spec=UserRepository[int])
    mock._model_class = User
    return mock


@pytest.fixture
def mock_password_service() -> MagicMock:
    """Provide a mocked PasswordHasher for testing."""
    mock = MagicMock(spec=PasswordHasher)
    mock.hash_password.return_value = "hashed_password"
    mock.verify_password.return_value = True
    return mock


@pytest.fixture
def user_service(
    mock_repository: AsyncMock, mock_password_service: MagicMock
) -> UserService[int]:
    """Provide a UserService instance with mocked dependencies."""
    return UserService(mock_repository, mock_password_service)


@pytest.fixture
def mock_user_service() -> AsyncMock:
    """Provide a mocked UserService for endpoint testing."""
    return AsyncMock(spec=UserService)


@pytest.fixture
def sample_users(regular_user: User, admin_user: User) -> list[User]:
    """Provide a list of sample users for testing."""
    return [regular_user, admin_user]


@pytest.fixture
def user_create_data_dict() -> dict[str, Any]:
    """Provide valid user creation data for API testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "password123",
        "role": "user",
    }


@pytest.fixture
def user_create_data(user_create_data_dict: dict[str, Any]) -> UserCreate:
    """Provide valid user creation data for service testing."""
    data = user_create_data_dict.copy()
    data["role"] = UserRole(data["role"])
    return UserCreate(**data)
