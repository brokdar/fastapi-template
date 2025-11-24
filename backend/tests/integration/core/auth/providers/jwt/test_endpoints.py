"""Integration tests for JWT authentication endpoints."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt as pyjwt
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.providers.jwt.schemas import TokenResponse
from app.domains.users.models import User


class TestLoginEndpoint:
    """Test suite for POST /auth/jwt/login endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("ensure_test_users")
    async def test_returns_tokens_with_valid_credentials(
        self,
        unauthorized_client: httpx.AsyncClient,
        normal_user_credentials: dict[str, str],
    ) -> None:
        """Test successful login returns access and refresh tokens."""
        response = await unauthorized_client.post(
            "/auth/jwt/login",
            data=normal_user_credentials,
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("ensure_test_users")
    async def test_returns_valid_token_structure(
        self,
        unauthorized_client: httpx.AsyncClient,
        normal_user_credentials: dict[str, str],
    ) -> None:
        """Test login tokens have valid JWT structure with three parts."""
        response = await unauthorized_client.post(
            "/auth/jwt/login",
            data=normal_user_credentials,
        )

        assert response.status_code == 200
        data = response.json()

        access_parts = data["access_token"].split(".")
        assert len(access_parts) == 3

        refresh_parts = data["refresh_token"].split(".")
        assert len(refresh_parts) == 3

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("ensure_test_users")
    async def test_raises_invalid_credentials_with_wrong_password(
        self,
        unauthorized_client: httpx.AsyncClient,
        normal_user_credentials: dict[str, str],
    ) -> None:
        """Test login fails with incorrect password."""
        response = await unauthorized_client.post(
            "/auth/jwt/login",
            data={
                "username": normal_user_credentials["username"],
                "password": "wrongpassword123",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_invalid_credentials_with_nonexistent_user(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test login fails with non-existent username."""
        response = await unauthorized_client.post(
            "/auth/jwt/login",
            data={
                "username": "nonexistentuser",
                "password": "anypassword123",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_inactive_user_error_when_user_inactive(
        self,
        unauthorized_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        normal_user_credentials: dict[str, str],
        test_session: AsyncSession,
    ) -> None:
        """Test login fails when user account is inactive."""
        normal_user, _ = ensure_test_users
        normal_user.is_active = False
        test_session.add(normal_user)
        await test_session.commit()

        try:
            response = await unauthorized_client.post(
                "/auth/jwt/login",
                data=normal_user_credentials,
            )

            assert response.status_code == 403
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "AUTHORIZATION_ERROR"
        finally:
            normal_user.is_active = True
            test_session.add(normal_user)
            await test_session.commit()

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("ensure_test_users")
    async def test_returns_different_tokens_for_different_users(
        self,
        unauthorized_client: httpx.AsyncClient,
        normal_user_credentials: dict[str, str],
        admin_user_credentials: dict[str, str],
    ) -> None:
        """Test different users receive different tokens."""
        normal_response = await unauthorized_client.post(
            "/auth/jwt/login",
            data=normal_user_credentials,
        )
        admin_response = await unauthorized_client.post(
            "/auth/jwt/login",
            data=admin_user_credentials,
        )

        assert normal_response.status_code == 200
        assert admin_response.status_code == 200

        normal_tokens = normal_response.json()
        admin_tokens = admin_response.json()

        assert normal_tokens["access_token"] != admin_tokens["access_token"]
        assert normal_tokens["refresh_token"] != admin_tokens["refresh_token"]


class TestRefreshEndpoint:
    """Test suite for POST /auth/jwt/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_returns_new_tokens_with_valid_refresh_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test refresh returns new access and refresh tokens."""
        response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_implements_token_rotation(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test refresh issues new tokens and old refresh token can be used once."""
        await asyncio.sleep(1.1)

        first_refresh = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )
        assert first_refresh.status_code == 200
        first_tokens = first_refresh.json()

        assert "access_token" in first_tokens
        assert "refresh_token" in first_tokens
        assert first_tokens["access_token"] != login_tokens.access_token
        assert first_tokens["refresh_token"] != login_tokens.refresh_token

        await asyncio.sleep(1.1)

        second_refresh = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": first_tokens["refresh_token"]},
        )
        assert second_refresh.status_code == 200
        second_tokens = second_refresh.json()

        assert second_tokens["access_token"] != first_tokens["access_token"]
        assert second_tokens["refresh_token"] != first_tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_raises_invalid_token_with_malformed_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        malformed_token: str,
    ) -> None:
        """Test refresh fails with malformed token."""
        response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": malformed_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_invalid_token_with_access_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test refresh fails when access token is used instead of refresh token."""
        response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.access_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_expired_token_with_expired_refresh_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        expired_refresh_token: str,
    ) -> None:
        """Test refresh fails with expired refresh token."""
        response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": expired_refresh_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_raises_user_not_found_when_user_deleted(
        self,
        unauthorized_client: httpx.AsyncClient,
        jwt_settings: dict[str, Any],
    ) -> None:
        """Test refresh fails when user referenced in token no longer exists."""
        now = datetime.now(UTC)
        payload = {
            "sub": "999999",
            "exp": int((now + timedelta(days=7)).timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        }
        token_for_nonexistent_user = pyjwt.encode(
            payload,
            jwt_settings["secret_key"],
            algorithm=jwt_settings["algorithm"],
        )

        response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": token_for_nonexistent_user},
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "RESOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_raises_inactive_user_error_when_user_inactive(
        self,
        unauthorized_client: httpx.AsyncClient,
        ensure_test_users: tuple[User, User],
        login_tokens: TokenResponse,
        test_session: AsyncSession,
    ) -> None:
        """Test refresh fails when user account is inactive."""
        normal_user, _ = ensure_test_users
        normal_user.is_active = False
        test_session.add(normal_user)
        await test_session.commit()

        try:
            response = await unauthorized_client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": login_tokens.refresh_token},
            )

            assert response.status_code == 403
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "AUTHORIZATION_ERROR"
        finally:
            normal_user.is_active = True
            test_session.add(normal_user)
            await test_session.commit()
