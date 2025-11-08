"""Test suite for user management API endpoints."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.core.pagination import Page
from app.dependencies import get_user_service
from app.domains.users.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.domains.users.models import User
from app.domains.users.schemas import UserResponse
from app.main import app


@pytest.fixture(autouse=True)
def setup_dependencies(mock_user_service: AsyncMock) -> Generator[None, None, None]:
    """Set up and tear down dependencies for each test."""
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    yield
    app.dependency_overrides = original_overrides


class TestGetUsersEndpoint:
    """Test suite for GET /users/ endpoint."""

    def test_returns_200_and_user_list_with_default_pagination(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        sample_users: list[User],
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful user list retrieval with default pagination."""
        mock_user_service.get_all.return_value = (sample_users, 2)

        response = unauthenticated_client.get(f"{api_prefix}/users/")

        assert response.status_code == status.HTTP_200_OK

        adapter = TypeAdapter(Page[UserResponse])
        user_page = adapter.validate_python(response.json())

        assert len(user_page.items) == 2
        assert user_page.pagination.total == 2
        assert user_page.pagination.limit == 10
        assert user_page.pagination.offset == 0
        assert user_page.items[0].username == "testuser"

        mock_user_service.get_all.assert_called_once()

    def test_returns_200_with_custom_pagination(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        sample_users: list[User],
        mock_user_service: AsyncMock,
    ) -> None:
        """Test user list retrieval with custom pagination parameters."""
        mock_user_service.get_all.return_value = (sample_users[:1], 50)

        response = unauthenticated_client.get(f"{api_prefix}/users/?offset=1&limit=1")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["items"]) == 1
        assert data["pagination"]["total"] == 50
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["offset"] == 1

        mock_user_service.get_all.assert_called_once()

    @pytest.mark.parametrize(
        ("offset", "limit", "expected_status"),
        [
            (-1, 10, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (0, 0, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (0, 101, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (0, -1, status.HTTP_422_UNPROCESSABLE_CONTENT),
        ],
        ids=[
            "negative_offset",
            "zero_limit",
            "excessive_limit",
            "negative_limit",
        ],
    )
    def test_returns_422_for_invalid_pagination_parameters(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        offset: int,
        limit: int,
        expected_status: int,
    ) -> None:
        """Test validation errors for invalid pagination parameters."""
        response = unauthenticated_client.get(
            f"{api_prefix}/users/?offset={offset}&limit={limit}"
        )
        assert response.status_code == expected_status


class TestGetUserEndpoint:
    """Test suite for GET /users/{user_id} endpoint."""

    def test_returns_200_and_user_when_exists(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        regular_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful user retrieval by ID."""
        mock_user_service.get_by_id.return_value = regular_user

        response = unauthenticated_client.get(f"{api_prefix}/users/1")

        assert response.status_code == status.HTTP_200_OK

        adapter = TypeAdapter(UserResponse)
        user_response = adapter.validate_python(response.json())

        assert user_response.id == 1
        assert user_response.username == "testuser"
        assert user_response.email == "test@example.com"
        assert user_response.full_name == "Test User"

        mock_user_service.get_by_id.assert_called_once_with(1)

    def test_returns_404_when_user_not_exists(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test 404 response when user doesn't exist."""
        mock_user_service.get_by_id.side_effect = UserNotFoundError("User not found")

        response = unauthenticated_client.get(f"{api_prefix}/users/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_user_service.get_by_id.assert_called_once_with(999)

    def test_returns_422_for_invalid_user_id(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
    ) -> None:
        """Test validation error for invalid user ID format."""
        response = unauthenticated_client.get(f"{api_prefix}/users/invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestCreateUserEndpoint:
    """Test suite for POST /users/ endpoint."""

    def test_returns_201_and_created_user(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        regular_user: User,
        user_create_data_dict: dict[str, Any],
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful user creation."""
        mock_user_service.create_user.return_value = regular_user

        response = unauthenticated_client.post(
            f"{api_prefix}/users/", json=user_create_data_dict
        )

        assert response.status_code == status.HTTP_201_CREATED

        adapter = TypeAdapter(UserResponse)
        created_user = adapter.validate_python(response.json())

        assert created_user.username == "testuser"
        assert created_user.email == "test@example.com"

        mock_user_service.create_user.assert_called_once()

    def test_returns_409_when_user_already_exists(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        user_create_data_dict: dict[str, Any],
        mock_user_service: AsyncMock,
    ) -> None:
        """Test conflict response when user already exists."""
        mock_user_service.create_user.side_effect = UserAlreadyExistsError(
            "User already exists"
        )

        response = unauthenticated_client.post(
            f"{api_prefix}/users/", json=user_create_data_dict
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.parametrize(
        ("invalid_data", "expected_status"),
        [
            ({}, status.HTTP_422_UNPROCESSABLE_CONTENT),
            (
                {"username": "ab", "email": "test@example.com", "password": "pass123"},
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
            (
                {
                    "username": "validuser",
                    "email": "invalid-email",
                    "password": "pass123",
                },
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
            (
                {
                    "username": "validuser",
                    "email": "test@example.com",
                    "password": "short",
                },
                status.HTTP_422_UNPROCESSABLE_CONTENT,
            ),
        ],
        ids=[
            "missing_fields",
            "username_too_short",
            "invalid_email",
            "password_too_short",
        ],
    )
    def test_returns_422_for_invalid_user_data(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        invalid_data: dict[str, Any],
        expected_status: int,
    ) -> None:
        """Test validation errors for invalid user creation data."""
        response = unauthenticated_client.post(
            f"{api_prefix}/users/", json=invalid_data
        )
        assert response.status_code == expected_status


class TestUpdateUserEndpoint:
    """Test suite for PATCH /users/{user_id} endpoint."""

    def test_returns_200_and_updated_user(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        regular_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful user update."""
        update_data = {"first_name": "Updated", "is_active": False}

        mock_user_service.update_user.return_value = regular_user

        response = unauthenticated_client.patch(
            f"{api_prefix}/users/1", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK

        adapter = TypeAdapter(UserResponse)
        updated_user = adapter.validate_python(response.json())

        assert updated_user.id == 1

        mock_user_service.update_user.assert_called_once()

    def test_returns_404_when_user_not_exists(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test 404 response when updating non-existent user."""
        update_data = {"first_name": "Updated"}

        mock_user_service.update_user.side_effect = UserNotFoundError("User not found")

        response = unauthenticated_client.patch(
            f"{api_prefix}/users/999", json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_409_on_conflict(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test conflict response when update creates duplicate."""
        update_data = {"email": "existing@example.com"}

        mock_user_service.update_user.side_effect = UserAlreadyExistsError(
            "Email already exists"
        )

        response = unauthenticated_client.patch(
            f"{api_prefix}/users/1", json=update_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT


class TestDeleteUserEndpoint:
    """Test suite for DELETE /users/{user_id} endpoint."""

    def test_returns_204_when_user_deleted(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful user deletion."""
        response = unauthenticated_client.delete(f"{api_prefix}/users/1")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""

        mock_user_service.delete_user.assert_called_once_with(1)

    def test_returns_404_when_user_not_exists(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test 404 response when deleting non-existent user."""
        mock_user_service.delete_user.side_effect = UserNotFoundError("User not found")

        response = unauthenticated_client.delete(f"{api_prefix}/users/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
