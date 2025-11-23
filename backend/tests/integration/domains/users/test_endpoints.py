"""Integration tests for user management endpoints."""

from typing import Any

import httpx
import pytest

from app.domains.users.models import User


class TestUsersCollection:
    """Test suite for /users/ collection endpoints."""

    @pytest.mark.asyncio
    async def test_lists_users_as_admin(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test admin successfully lists users with pagination format."""
        response = await admin_client.get("/users/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        assert data["pagination"]["total"] >= 2
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["limit"] == 10
        assert isinstance(data["pagination"]["has_next"], bool)
        assert isinstance(data["pagination"]["has_prev"], bool)
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("offset", "limit", "expected_min_items"),
        [
            (0, 10, 2),
            (0, 1, 1),
            (1, 10, 1),
            (0, 100, 2),
        ],
        ids=["default_pagination", "limit_one", "offset_one", "max_limit"],
    )
    async def test_lists_users_with_pagination(
        self,
        admin_client: httpx.AsyncClient,
        offset: int,
        limit: int,
        expected_min_items: int,
    ) -> None:
        """Test pagination parameters work correctly."""
        response = await admin_client.get(
            "/users/",
            params={"offset": offset, "limit": limit},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["offset"] == offset
        assert data["pagination"]["limit"] == limit
        assert len(data["items"]) >= expected_min_items

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_non_admin_lists_users(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test non-admin user cannot list users."""
        response = await authenticated_client.get("/users/")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.asyncio
    async def test_creates_user_as_admin(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test admin successfully creates new user."""
        response = await admin_client.post(
            "/users/",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": "user",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_raises_conflict_when_duplicate_email(
        self,
        admin_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test email uniqueness constraint."""
        response = await admin_client.post(
            "/users/",
            json={
                "username": "otheruser",
                "email": normal_user_data["email"],
                "password": "password123",
                "role": "user",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_raises_conflict_when_duplicate_username(
        self,
        admin_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test username uniqueness constraint."""
        response = await admin_client.post(
            "/users/",
            json={
                "username": normal_user_data["username"],
                "email": "other@example.com",
                "password": "password123",
                "role": "user",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("invalid_username", "expected_status"),
        [
            ("ab", 422),
            ("a" * 13, 422),
            ("user@name", 422),
            ("user name", 422),
            ("user-name", 422),
        ],
        ids=["too_short", "too_long", "at_symbol", "space", "hyphen"],
    )
    async def test_raises_validation_error_for_invalid_username(
        self,
        admin_client: httpx.AsyncClient,
        invalid_username: str,
        expected_status: int,
    ) -> None:
        """Test username validation for various invalid inputs."""
        response = await admin_client.post(
            "/users/",
            json={
                "username": invalid_username,
                "email": "test@example.com",
                "password": "password123",
                "role": "user",
            },
        )

        assert response.status_code == expected_status
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_non_admin_creates_user(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test non-admin user cannot create users."""
        response = await authenticated_client.post(
            "/users/",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "role": "user",
            },
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"


class TestUserMe:
    """Test suite for /users/me profile endpoints."""

    @pytest.mark.asyncio
    async def test_gets_own_profile_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test authenticated user retrieves own profile."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]
        assert data["email"] == normal_user_data["email"]
        assert data["first_name"] == normal_user_data["first_name"]
        assert data["last_name"] == normal_user_data["last_name"]
        assert data["role"] == normal_user_data["role"]
        assert "id" in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails."""
        response = await unauthorized_client.get("/users/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_updates_own_profile_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test authenticated user updates own profile."""
        response = await authenticated_client.patch(
            "/users/me",
            json={
                "first_name": "Updated",
                "last_name": "Name",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    @pytest.mark.asyncio
    async def test_updates_partial_fields_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test partial profile update works correctly."""
        response = await authenticated_client.patch(
            "/users/me",
            json={"first_name": "OnlyFirst"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "OnlyFirst"

    @pytest.mark.asyncio
    async def test_raises_conflict_when_updating_to_existing_email(
        self,
        authenticated_client: httpx.AsyncClient,
        admin_user_data: dict[str, Any],
    ) -> None:
        """Test email conflict when updating to another user's email."""
        response = await authenticated_client.patch(
            "/users/me",
            json={"email": admin_user_data["email"]},
        )

        assert response.status_code == 409
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_allows_keeping_same_email_on_update(
        self,
        authenticated_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test user can update profile with same email."""
        response = await authenticated_client.patch(
            "/users/me",
            json={
                "email": normal_user_data["email"],
                "first_name": "SameEmail",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == normal_user_data["email"]
        assert data["first_name"] == "SameEmail"


class TestUserOperations:
    """Test suite for /users/{user_id} operation endpoints."""

    @pytest.mark.asyncio
    async def test_gets_user_by_id_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test admin retrieves specific user by ID."""
        normal_user, _ = ensure_test_users

        response = await admin_client.get(f"/users/{normal_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == normal_user.id
        assert data["username"] == normal_user_data["username"]
        assert data["email"] == normal_user_data["email"]

    @pytest.mark.asyncio
    async def test_raises_not_found_for_nonexistent_user_id(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test 404 error for non-existent user ID."""
        response = await admin_client.get("/users/999999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_non_admin_gets_user(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test non-admin cannot retrieve user by ID."""
        _, admin_user = ensure_test_users

        response = await authenticated_client.get(f"/users/{admin_user.id}")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.asyncio
    async def test_updates_user_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test admin updates user fields successfully."""
        normal_user, _ = ensure_test_users

        response = await admin_client.patch(
            f"/users/{normal_user.id}",
            json={
                "first_name": "AdminUpdated",
                "last_name": "UserName",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "AdminUpdated"
        assert data["last_name"] == "UserName"
        assert data["id"] == normal_user.id

    @pytest.mark.asyncio
    async def test_updates_user_role_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test admin modifies user role successfully."""
        normal_user, _ = ensure_test_users

        response = await admin_client.patch(
            f"/users/{normal_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["id"] == normal_user.id

    @pytest.mark.asyncio
    async def test_raises_conflict_when_updating_to_duplicate_email(
        self,
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        admin_user_data: dict[str, Any],
    ) -> None:
        """Test email uniqueness constraint during update."""
        normal_user, _ = ensure_test_users

        response = await admin_client.patch(
            f"/users/{normal_user.id}",
            json={"email": admin_user_data["email"]},
        )

        assert response.status_code == 409
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_deletes_user_successfully_as_admin(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test admin deletes user and receives 204 status."""
        create_response = await admin_client.post(
            "/users/",
            json={
                "username": "tobedeleted",
                "email": "tobedeleted@example.com",
                "password": "password123",
                "role": "user",
            },
        )
        assert create_response.status_code == 201
        user_id = create_response.json()["id"]

        response = await admin_client.delete(f"/users/{user_id}")

        assert response.status_code == 204
        assert response.content == b""

    @pytest.mark.asyncio
    async def test_raises_not_found_when_deleting_nonexistent_user(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test 404 error when deleting non-existent user."""
        response = await admin_client.delete("/users/999999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_raises_forbidden_when_non_admin_deletes_user(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test non-admin cannot delete users."""
        _, admin_user = ensure_test_users

        response = await authenticated_client.delete(f"/users/{admin_user.id}")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"
