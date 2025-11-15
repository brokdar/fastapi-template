"""Test suite for JWT authentication router."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.router import create_jwt_router
from app.core.auth.providers.jwt.schemas import TokenResponse
from app.domains.users.models import User


class TestCreateJWTRouter:
    """Test suite for JWT router creation."""

    def test_create_jwt_router_returns_router(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test create_jwt_router returns APIRouter instance."""
        router = create_jwt_router(jwt_provider)

        assert isinstance(router, APIRouter)

    def test_create_jwt_router_has_correct_prefix(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test router has correct prefix."""
        router = create_jwt_router(jwt_provider)

        assert router.prefix == "/jwt"

    def test_create_jwt_router_has_two_endpoints(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test router has login and refresh endpoints."""
        router = create_jwt_router(jwt_provider)

        route_paths = [route.path for route in router.routes if hasattr(route, "path")]
        assert len(route_paths) == 2

    def test_create_jwt_router_works_with_int_id(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test router creation with int ID type."""
        router = create_jwt_router(jwt_provider)

        assert isinstance(router, APIRouter)

    def test_create_jwt_router_works_with_uuid_id(
        self, uuid_jwt_provider: JWTAuthProvider[UUID]
    ) -> None:
        """Test router creation with UUID ID type."""
        router = create_jwt_router(uuid_jwt_provider)

        assert isinstance(router, APIRouter)


class TestLoginEndpoint:
    """Test suite for login endpoint registration."""

    def test_login_endpoint_exists_in_router(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test login endpoint is registered in router."""
        router = create_jwt_router(jwt_provider)

        login_exists = any(
            hasattr(route, "path")
            and "/login" in route.path
            and hasattr(route, "endpoint")
            for route in router.routes
        )
        assert login_exists

    def test_login_endpoint_accepts_post_method(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test login endpoint accepts POST method."""
        router = create_jwt_router(jwt_provider)

        login_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/login" in route.path:
                login_route = route
                break

        assert login_route is not None
        assert isinstance(login_route, APIRoute)
        assert "POST" in login_route.methods

    def test_login_endpoint_has_correct_response_model(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test login endpoint declares correct response model."""
        router = create_jwt_router(jwt_provider)

        login_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/login" in route.path:
                login_route = route
                break

        assert login_route is not None
        assert isinstance(login_route, APIRoute)
        assert login_route.response_model == TokenResponse

    def test_login_endpoint_has_summary(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test login endpoint has descriptive summary."""
        router = create_jwt_router(jwt_provider)

        login_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/login" in route.path:
                login_route = route
                break

        assert login_route is not None
        assert isinstance(login_route, APIRoute)
        assert login_route.summary == "Login with username and password"


class TestRefreshEndpoint:
    """Test suite for token refresh endpoint registration."""

    def test_refresh_endpoint_exists_in_router(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test refresh endpoint is registered in router."""
        router = create_jwt_router(jwt_provider)

        refresh_exists = any(
            hasattr(route, "path")
            and "/refresh" in route.path
            and hasattr(route, "endpoint")
            for route in router.routes
        )
        assert refresh_exists

    def test_refresh_endpoint_accepts_post_method(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test refresh endpoint accepts POST method."""
        router = create_jwt_router(jwt_provider)

        refresh_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/refresh" in route.path:
                refresh_route = route
                break

        assert refresh_route is not None
        assert isinstance(refresh_route, APIRoute)
        assert "POST" in refresh_route.methods

    def test_refresh_endpoint_has_correct_response_model(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test refresh endpoint declares correct response model."""
        router = create_jwt_router(jwt_provider)

        refresh_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/refresh" in route.path:
                refresh_route = route
                break

        assert refresh_route is not None
        assert isinstance(refresh_route, APIRoute)
        assert refresh_route.response_model == TokenResponse

    def test_refresh_endpoint_has_summary(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test refresh endpoint has descriptive summary."""
        router = create_jwt_router(jwt_provider)

        refresh_route = None
        for route in router.routes:
            if hasattr(route, "path") and "/refresh" in route.path:
                refresh_route = route
                break

        assert refresh_route is not None
        assert isinstance(refresh_route, APIRoute)
        assert refresh_route.summary == "Refresh access token"


class TestRouterIntegration:
    """Test suite for router integration with provider."""

    def test_router_binds_provider_via_closure(
        self,
        jwt_provider: JWTAuthProvider[int],
    ) -> None:
        """Test router endpoints have access to provider instance."""
        router = create_jwt_router(jwt_provider)

        assert len(router.routes) > 0

        for route in router.routes:
            if hasattr(route, "endpoint") and hasattr(route.endpoint, "__closure__"):
                closure_vars = [
                    cell.cell_contents
                    for cell in route.endpoint.__closure__
                    if hasattr(cell, "cell_contents")
                ]
                provider_found = any(
                    isinstance(var, JWTAuthProvider) for var in closure_vars
                )
                if provider_found:
                    assert True
                    return

        pytest.fail("No route found with provider in closure")

    def test_router_can_be_included_in_app(
        self, jwt_provider: JWTAuthProvider[int]
    ) -> None:
        """Test router can be included in FastAPI application."""
        from fastapi import FastAPI

        router = create_jwt_router(jwt_provider)
        app = FastAPI()

        app.include_router(router, prefix="/auth")

        route_paths = [route.path for route in app.routes if hasattr(route, "path")]
        assert any("/auth/jwt/login" in path for path in route_paths)
        assert any("/auth/jwt/refresh" in path for path in route_paths)


class TestLoginEndpointBehavior:
    """Test suite for login endpoint behavior with HTTP requests."""

    @pytest.mark.asyncio
    async def test_authenticates_user_with_valid_credentials(
        self,
        jwt_provider: JWTAuthProvider[int],
        sample_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful login returns TokenResponse."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_name.return_value = sample_user
        mock_user_service.verify_password.return_value = True

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/login",
                data={"username": "testuser", "password": "testpass"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        mock_user_service.get_by_name.assert_called_once_with("testuser")
        mock_user_service.verify_password.assert_called_once_with(
            sample_user, "testpass"
        )

    @pytest.mark.asyncio
    async def test_raises_invalid_credentials_error_when_user_not_found(
        self,
        jwt_provider: JWTAuthProvider[int],
        mock_user_service: AsyncMock,
    ) -> None:
        """Test login fails with InvalidCredentialsError for non-existent user."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service
        from app.domains.users.exceptions import UserNotFoundError

        mock_user_service.get_by_name.side_effect = UserNotFoundError("User not found")

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/login",
                data={"username": "nonexistent", "password": "testpass"},
            )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_raises_invalid_credentials_error_when_password_incorrect(
        self,
        jwt_provider: JWTAuthProvider[int],
        sample_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test login fails with InvalidCredentialsError for wrong password."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_name.return_value = sample_user
        mock_user_service.verify_password.return_value = False

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/login",
                data={"username": "testuser", "password": "wrongpass"},
            )

        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_raises_inactive_user_error_when_user_inactive(
        self,
        jwt_provider: JWTAuthProvider[int],
        inactive_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test login fails with InactiveUserError for inactive account."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_name.return_value = inactive_user
        mock_user_service.verify_password.return_value = True

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/login",
                data={"username": "inactiveuser", "password": "testpass"},
            )

        assert response.status_code == 403
        assert "inactive" in response.json()["error"]["message"].lower()


class TestRefreshEndpointBehavior:
    """Test suite for refresh endpoint behavior with HTTP requests."""

    @pytest.mark.asyncio
    async def test_refreshes_token_with_valid_refresh_token(
        self,
        jwt_provider: JWTAuthProvider[int],
        valid_refresh_token: str,
        sample_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test successful token refresh returns new TokenResponse."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_id.return_value = sample_user

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": valid_refresh_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        mock_user_service.parse_id.assert_called_once_with("1")
        mock_user_service.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_returns_different_tokens_on_refresh(
        self,
        jwt_provider: JWTAuthProvider[int],
        valid_refresh_token: str,
        sample_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test token rotation produces both access and refresh tokens."""
        import asyncio

        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_id.return_value = sample_user

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        await asyncio.sleep(1)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": valid_refresh_token},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != data["refresh_token"]
        assert data["access_token"] != valid_refresh_token

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_malformed(
        self,
        jwt_provider: JWTAuthProvider[int],
        malformed_token: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test refresh fails with InvalidTokenError for malformed token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": malformed_token},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_token_expired_error_when_expired(
        self,
        jwt_provider: JWTAuthProvider[int],
        expired_token: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test refresh fails with TokenExpiredError for expired token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": expired_token},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_wrong_type(
        self,
        jwt_provider: JWTAuthProvider[int],
        valid_access_token: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test refresh fails when using access token instead of refresh token."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": valid_access_token},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_user_not_found_error_when_user_deleted(
        self,
        jwt_provider: JWTAuthProvider[int],
        valid_refresh_token: str,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test refresh fails with UserNotFoundError when user deleted."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service
        from app.domains.users.exceptions import UserNotFoundError

        mock_user_service.get_by_id.side_effect = UserNotFoundError("User not found")

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": valid_refresh_token},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_inactive_user_error_when_user_deactivated(
        self,
        jwt_provider: JWTAuthProvider[int],
        valid_refresh_token: str,
        inactive_user: User,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test refresh fails with InactiveUserError when user deactivated."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from app.core.exceptions.handlers import setup_exception_handlers
        from app.dependencies import get_user_service

        mock_user_service.get_by_id.return_value = inactive_user

        router = create_jwt_router(jwt_provider)
        app = FastAPI()
        setup_exception_handlers(app)
        app.include_router(router, prefix="/auth")
        app.dependency_overrides[get_user_service] = lambda: mock_user_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/auth/jwt/refresh",
                json={"refresh_token": valid_refresh_token},
            )

        assert response.status_code == 403
        assert "inactive" in response.json()["error"]["message"].lower()
