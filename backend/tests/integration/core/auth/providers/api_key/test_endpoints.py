"""Integration tests for API key management endpoints."""

import httpx
import pytest

from app.domains.users.models import User


class TestCreateAPIKey:
    """Test suite for POST /auth/api-keys endpoint."""

    @pytest.mark.asyncio
    async def test_creates_api_key_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test authenticated user creates API key successfully."""
        response = await authenticated_client.post(
            "/auth/api-keys",
            json={"name": "My Test Key"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Test Key"
        assert "id" in data
        assert "secret_key" in data
        assert data["secret_key"].startswith("sk_")
        assert len(data["secret_key"]) == 67
        assert "key_prefix" in data
        assert "created_at" in data
        assert data["expires_at"] is not None
        assert data["last_used_at"] is None

    @pytest.mark.asyncio
    async def test_creates_api_key_with_expiration(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test creating API key with custom expiration."""
        response = await authenticated_client.post(
            "/auth/api-keys",
            json={"name": "Expiring Key", "expires_in_days": 30},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Expiring Key"
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails with 401."""
        response = await unauthorized_client.post(
            "/auth/api-keys",
            json={"name": "Unauthorized Key"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


class TestListAPIKeys:
    """Test suite for GET /auth/api-keys endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("created_api_key")
    async def test_lists_api_keys_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test authenticated user lists their API keys."""
        response = await authenticated_client.get("/auth/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        key = data[0]
        assert "id" in key
        assert "name" in key
        assert "key_prefix" in key
        assert "created_at" in key
        assert "secret_key" not in key

    @pytest.mark.asyncio
    async def test_lists_empty_when_no_keys(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test empty list returned when user has no API keys."""
        response = await authenticated_client.get("/auth/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails with 401."""
        response = await unauthorized_client.get("/auth/api-keys")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


class TestDeleteAPIKey:
    """Test suite for DELETE /auth/api-keys/{key_id} endpoint."""

    @pytest.mark.asyncio
    async def test_deletes_api_key_successfully(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test authenticated user deletes their API key."""
        create_response = await authenticated_client.post(
            "/auth/api-keys",
            json={"name": "Key To Delete"},
        )
        assert create_response.status_code == 201
        key_id = create_response.json()["id"]

        response = await authenticated_client.delete(f"/auth/api-keys/{key_id}")

        assert response.status_code == 204
        assert response.content == b""

    @pytest.mark.asyncio
    async def test_raises_not_found_for_nonexistent_key(
        self,
        authenticated_client: httpx.AsyncClient,
    ) -> None:
        """Test 404 error when deleting non-existent API key."""
        response = await authenticated_client.delete("/auth/api-keys/999999")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails with 401."""
        response = await unauthorized_client.delete("/auth/api-keys/1")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


class TestAdminListUserAPIKeys:
    """Test suite for GET /auth/api-keys/users/{user_id} endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("created_api_key")
    async def test_lists_user_api_keys_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test admin lists another user's API keys."""
        normal_user, _ = ensure_test_users

        response = await admin_client.get(f"/auth/api-keys/users/{normal_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        key = data[0]
        assert "id" in key
        assert "user_id" in key
        assert key["user_id"] == normal_user.id
        assert "name" in key
        assert "key_prefix" in key

    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test non-admin user cannot list other user's API keys."""
        _, admin_user = ensure_test_users

        response = await authenticated_client.get(
            f"/auth/api-keys/users/{admin_user.id}"
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails with 401."""
        response = await unauthorized_client.get("/auth/api-keys/users/1")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


class TestAdminDeleteUserAPIKey:
    """Test suite for DELETE /auth/api-keys/users/{user_id}/{key_id} endpoint."""

    @pytest.mark.asyncio
    async def test_deletes_user_api_key_as_admin(
        self,
        admin_client: httpx.AsyncClient,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test admin deletes another user's API key."""
        normal_user, _ = ensure_test_users

        create_response = await authenticated_client.post(
            "/auth/api-keys",
            json={"name": "Admin Delete Target"},
        )
        assert create_response.status_code == 201
        key_id = create_response.json()["id"]

        response = await admin_client.delete(
            f"/auth/api-keys/users/{normal_user.id}/{key_id}"
        )

        assert response.status_code == 204
        assert response.content == b""

    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test non-admin user cannot delete other user's API keys."""
        _, admin_user = ensure_test_users

        response = await authenticated_client.delete(
            f"/auth/api-keys/users/{admin_user.id}/1"
        )

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_unauthorized_without_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test unauthenticated request fails with 401."""
        response = await unauthorized_client.delete("/auth/api-keys/users/1/1")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"
