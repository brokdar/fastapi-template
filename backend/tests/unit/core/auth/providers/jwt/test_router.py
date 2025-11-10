"""Test suite for JWT authentication router."""

from uuid import UUID

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.router import create_jwt_router
from app.core.auth.providers.jwt.schemas import TokenResponse


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
