"""Shared fixtures for authentication tests."""

from collections.abc import Callable
from inspect import Parameter, Signature
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, FastAPI, Request

from app.core.auth.providers.base import AuthProvider
from app.core.auth.services import AuthService
from app.domains.users.models import User
from app.domains.users.services import UserService


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
        from fastapi.security.base import SecurityBase

        provider = Mock(spec=AuthProvider)
        provider.name = kwargs.get("name", "test_provider")
        provider.can_authenticate.return_value = kwargs.get("can_authenticate", False)
        provider.authenticate = AsyncMock(
            return_value=kwargs.get("authenticate_return")
        )
        provider.get_router.return_value = kwargs.get("router", APIRouter())
        provider.get_security_scheme.return_value = kwargs.get(
            "security_scheme", Mock(spec=SecurityBase)
        )
        return provider

    return _create_provider


@pytest.fixture
def sample_signature() -> Signature:
    """Provide standard Request and UserService signature."""
    return Signature(
        [
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            Parameter(
                "user_service", Parameter.POSITIONAL_OR_KEYWORD, annotation=UserService
            ),
        ]
    )


@pytest.fixture
def simple_signature() -> Signature:
    """Provide single parameter signature."""
    return Signature(
        [
            Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=int),
        ]
    )


@pytest.fixture
def complex_signature() -> Signature:
    """Provide signature with defaults and annotations."""
    return Signature(
        [
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            Parameter("param1", Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
            Parameter(
                "param2",
                Parameter.POSITIONAL_OR_KEYWORD,
                annotation=str | None,
                default=None,
            ),
        ]
    )


@pytest.fixture
def signature_with_return() -> Signature:
    """Provide signature with explicit return annotation."""
    return Signature(
        [Parameter("x", Parameter.POSITIONAL_OR_KEYWORD, annotation=str)],
        return_annotation=User,
    )
