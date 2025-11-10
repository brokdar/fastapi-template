"""Shared fixtures for authentication tests."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, FastAPI, Request

from app.core.auth.providers.base import AuthProvider
from app.core.auth.services import AuthService


@pytest.fixture
def mock_request() -> Mock:
    """Provide a mocked FastAPI Request."""
    request = Mock(spec=Request)
    request.url.path = "/test"
    request.method = "GET"
    return request


@pytest.fixture
def mock_user_service_dependency() -> Callable[[], AsyncMock]:
    """Provide a callable that returns mocked UserService."""

    def _dependency() -> AsyncMock:
        return AsyncMock()

    return _dependency


@pytest.fixture
def mock_auth_provider() -> Mock:
    """Provide a mocked AuthProvider."""
    provider = Mock(spec=AuthProvider)
    provider.name = "test_provider"
    provider.can_authenticate.return_value = False
    provider.authenticate = AsyncMock(return_value=None)
    provider.get_router.return_value = APIRouter()
    return provider


@pytest.fixture
def mock_fastapi_app() -> Mock:
    """Provide a mocked FastAPI application."""
    app = Mock(spec=FastAPI)
    app.include_router = Mock()
    return app


@pytest.fixture
def auth_service(
    mock_user_service_dependency: Callable[[], AsyncMock],
) -> AuthService[int]:
    """Provide AuthService instance with no providers."""
    return AuthService(
        get_user_service=mock_user_service_dependency,
        providers=[],
    )


@pytest.fixture
def create_auth_provider() -> Callable[..., Mock]:
    """Factory function to create mock AuthProvider instances."""

    def _create_provider(**kwargs: Any) -> Mock:
        provider = Mock(spec=AuthProvider)
        provider.name = kwargs.get("name", "test_provider")
        provider.can_authenticate.return_value = kwargs.get("can_authenticate", False)
        provider.authenticate = AsyncMock(
            return_value=kwargs.get("authenticate_return")
        )
        provider.get_router.return_value = kwargs.get("router", APIRouter())
        return provider

    return _create_provider
