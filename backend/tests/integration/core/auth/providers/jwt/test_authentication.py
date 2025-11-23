"""Integration tests for JWT authentication flow."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt as pyjwt
import pytest

from app.core.auth.providers.jwt.schemas import TokenResponse
from app.domains.users.models import User


class TestJWTAuthentication:
    """Test suite for JWT authentication flow on protected endpoints."""

    @pytest.mark.asyncio
    async def test_authenticates_request_with_valid_access_token(
        self,
        authenticated_client: httpx.AsyncClient,
        normal_user_data: dict[str, Any],
    ) -> None:
        """Test protected endpoint access with valid JWT token."""
        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == normal_user_data["username"]

    @pytest.mark.asyncio
    async def test_rejects_request_with_invalid_token(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test 401 error with invalid JWT token."""
        response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_with_expired_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        expired_access_token: str,
    ) -> None:
        """Test 401 error with expired access token."""
        response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {expired_access_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_with_refresh_token_as_access(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test 401 error when refresh token is used as access token."""
        response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {login_tokens.refresh_token}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_without_bearer_prefix(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test 401 error when Bearer prefix is missing."""
        response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": login_tokens.access_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_without_authorization_header(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test 401 error when Authorization header is missing."""
        response = await unauthorized_client.get("/users/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_with_token_for_deleted_user(
        self,
        unauthorized_client: httpx.AsyncClient,
        jwt_settings: dict[str, Any],
    ) -> None:
        """Test 401 error when token references non-existent user."""
        now = datetime.now(UTC)
        payload = {
            "sub": "999999",
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
        }
        token_for_nonexistent_user = pyjwt.encode(
            payload,
            jwt_settings["secret_key"],
            algorithm=jwt_settings["algorithm"],
        )

        response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token_for_nonexistent_user}"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_rejects_request_with_token_for_inactive_user(
        self,
        unauthorized_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        login_tokens: TokenResponse,
        test_session: Any,
    ) -> None:
        """Test 401 error when token references inactive user."""
        normal_user, _ = ensure_test_users
        normal_user.is_active = False
        test_session.add(normal_user)
        await test_session.commit()

        try:
            response = await unauthorized_client.get(
                "/users/me",
                headers={"Authorization": f"Bearer {login_tokens.access_token}"},
            )

            assert response.status_code == 401
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "AUTHENTICATION_ERROR"
        finally:
            normal_user.is_active = True
            test_session.add(normal_user)
            await test_session.commit()


class TestTokenAccessControl:
    """Test suite for token-based access control scenarios."""

    @pytest.mark.asyncio
    async def test_accesses_user_specific_data_with_token(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test authenticated user accesses their own data."""
        normal_user, _ = ensure_test_users

        response = await authenticated_client.get("/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == normal_user.id

    @pytest.mark.asyncio
    async def test_admin_accesses_admin_endpoints_with_token(
        self,
        admin_client: httpx.AsyncClient,
    ) -> None:
        """Test admin user accesses admin-only endpoints."""
        response = await admin_client.get("/users/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert data["pagination"]["total"] >= 2

    @pytest.mark.asyncio
    async def test_regular_user_denied_admin_endpoints(
        self,
        authenticated_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
    ) -> None:
        """Test regular user denied access to admin endpoints."""
        _, admin_user = ensure_test_users
        assert admin_user.id is not None

        response = await authenticated_client.get(f"/users/{admin_user.id}")

        assert response.status_code == 403
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHORIZATION_ERROR"
