"""Integration tests for JWT token blacklist functionality."""

import httpx
import pytest

from app.core.auth.providers.jwt.schemas import TokenResponse


class TestLogoutEndpoint:
    """Test suite for POST /auth/jwt/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_returns_success(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test logout endpoint returns success response."""
        response = await unauthorized_client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"

    @pytest.mark.asyncio
    async def test_logout_requires_authentication(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test logout endpoint requires valid authentication."""
        response = await unauthorized_client.post("/auth/jwt/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logged_out_token_rejected_for_protected_endpoints(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that blacklisted access token is rejected on subsequent requests."""
        logout_response = await unauthorized_client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )
        assert logout_response.status_code == 200

        second_logout_response = await unauthorized_client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )

        assert second_logout_response.status_code == 401

    @pytest.mark.asyncio
    async def test_logged_out_token_rejected_for_user_endpoints(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that blacklisted token cannot access protected user endpoints."""
        logout_response = await unauthorized_client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )
        assert logout_response.status_code == 200

        me_response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )

        assert me_response.status_code == 401


class TestRefreshTokenRotationBlacklist:
    """Test suite for refresh token blacklisting during token rotation."""

    @pytest.mark.asyncio
    async def test_old_refresh_token_rejected_after_rotation(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that old refresh token is blacklisted after rotation."""
        first_refresh_response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )
        assert first_refresh_response.status_code == 200

        second_refresh_response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )

        assert second_refresh_response.status_code == 401
        data = second_refresh_response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_new_tokens_work_after_rotation(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that new tokens from rotation work correctly."""
        refresh_response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()

        me_response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me_response.status_code == 200

        second_refresh_response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": new_tokens["refresh_token"]},
        )
        assert second_refresh_response.status_code == 200

    @pytest.mark.asyncio
    async def test_chain_of_token_rotations(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that multiple consecutive token rotations work correctly."""
        current_refresh_token = login_tokens.refresh_token
        previous_tokens: list[str] = []

        for i in range(3):
            response = await unauthorized_client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": current_refresh_token},
            )
            assert response.status_code == 200, f"Refresh {i + 1} failed"

            data = response.json()
            previous_tokens.append(current_refresh_token)
            current_refresh_token = data["refresh_token"]

        for idx, old_token in enumerate(previous_tokens):
            response = await unauthorized_client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": old_token},
            )
            assert response.status_code == 401, (
                f"Old token {idx + 1} should be rejected"
            )


class TestLogoutWithRefreshInteraction:
    """Test interactions between logout and refresh token blacklisting."""

    @pytest.mark.asyncio
    async def test_logout_does_not_affect_refresh_token(
        self,
        unauthorized_client: httpx.AsyncClient,
        login_tokens: TokenResponse,
    ) -> None:
        """Test that logging out only blacklists access token, not refresh token."""
        logout_response = await unauthorized_client.post(
            "/auth/jwt/logout",
            headers={"Authorization": f"Bearer {login_tokens.access_token}"},
        )
        assert logout_response.status_code == 200

        refresh_response = await unauthorized_client.post(
            "/auth/jwt/refresh",
            json={"refresh_token": login_tokens.refresh_token},
        )
        assert refresh_response.status_code == 200

        new_tokens = refresh_response.json()
        me_response = await unauthorized_client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me_response.status_code == 200
