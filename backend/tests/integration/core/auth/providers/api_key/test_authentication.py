"""Integration tests for API key authentication flow."""

from typing import Any

import httpx
import pytest

from app.core.auth.providers.api_key.schemas import APIKeyCreateResponse
from app.domains.users.models import User
from app.main import app


class TestAPIKeyAuthentication:
    """Test suite for API key authentication flow."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("override_get_session")
    async def test_authenticates_with_valid_api_key(
        self,
        created_api_key: tuple[APIKeyCreateResponse, str],
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test access to protected endpoint with valid API key."""
        _, secret_key = created_api_key
        normal_user, _ = ensure_test_users

        login_response = await admin_client.post(
            "/auth/jwt/login",
            data={"username": "testadmin", "password": "testpass123"},
        )
        jwt_token = login_response.json()["access_token"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver/api/v1",
            headers={"X-API-Key": secret_key, "Authorization": f"Bearer {jwt_token}"},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]
        assert data["id"] == normal_user.id

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("override_get_session")
    async def test_raises_unauthorized_with_invalid_api_key(
        self,
    ) -> None:
        """Test 401 error with invalid API key."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver/api/v1",
            headers={
                "X-API-Key": "sk_invalid_key_that_is_not_valid_at_all_12345678901234567890"
            },
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("override_get_session")
    async def test_raises_unauthorized_with_malformed_api_key(
        self,
    ) -> None:
        """Test 401 error with malformed API key format."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver/api/v1",
            headers={"X-API-Key": "not_a_valid_key"},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_unauthorized_with_expired_api_key(
        self,
        authenticated_client: httpx.AsyncClient,
        test_session: Any,
    ) -> None:
        """Test 401 error when API key has expired."""
        from datetime import UTC, datetime, timedelta

        from app.core.auth.providers.api_key.models import APIKey

        create_response = await authenticated_client.post(
            "/auth/api-keys",
            json={"name": "Expiring Key", "expires_in_days": 1},
        )
        assert create_response.status_code == 201
        secret_key = create_response.json()["secret_key"]
        key_id = create_response.json()["id"]

        result = await test_session.get(APIKey, key_id)
        if result:
            result.expires_at = datetime.now(UTC) - timedelta(days=1)
            test_session.add(result)
            await test_session.commit()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver/api/v1",
            headers={"X-API-Key": secret_key},
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"


class TestMultiProviderAuthentication:
    """Test suite for multi-provider authentication scenarios."""

    @pytest.mark.asyncio
    async def test_authenticates_with_jwt_when_no_api_key(
        self,
        authenticated_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test JWT authentication works when API key is not provided."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("override_get_session")
    async def test_api_key_takes_precedence_over_jwt(
        self,
        created_api_key: tuple[APIKeyCreateResponse, str],
        admin_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test API key authentication takes precedence when both are provided."""
        _, secret_key = created_api_key
        normal_user, _ = ensure_test_users

        login_response = await admin_client.post(
            "/auth/jwt/login",
            data={
                "username": "testadmin",
                "password": "testpass123",
            },
        )
        jwt_token = login_response.json()["access_token"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver/api/v1",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "X-API-Key": secret_key,
            },
        ) as client:
            response = await client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]
        assert data["id"] == normal_user.id
