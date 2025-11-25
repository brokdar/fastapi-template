"""Test suite for API Key authentication provider."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, Request
from fastapi.security import APIKeyHeader

from app.core.auth.providers.api_key.exceptions import (
    APIKeyExpiredError,
    InvalidAPIKeyError,
)
from app.core.auth.providers.api_key.provider import APIKeyProvider
from app.core.auth.providers.api_key.services import APIKeyService
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import User


@pytest.fixture
def mock_get_api_key_service() -> Mock:
    """Provide mock get_api_key_service callable for router creation."""
    return Mock()


@pytest.fixture
def api_key_provider(mock_get_api_key_service: Mock) -> APIKeyProvider:
    """Provide APIKeyProvider instance with default settings."""
    return APIKeyProvider(get_api_key_service=mock_get_api_key_service)


@pytest.fixture
def sample_user() -> User:
    """Provide sample User instance for testing."""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$KIXqZHpJxV5XnV2Z8ZzJXe",
        is_active=True,
    )


@pytest.fixture
def inactive_user() -> User:
    """Provide inactive User instance for testing."""
    return User(
        id=2,
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password="$2b$12$KIXqZHpJxV5XnV2Z8ZzJXe",
        is_active=False,
    )


@pytest.fixture
def mock_user_service() -> AsyncMock:
    """Provide mocked AuthenticationUserService."""
    service = AsyncMock()
    service.parse_id = Mock(side_effect=lambda x: int(x))
    return service


@pytest.fixture
def mock_request_with_api_key() -> Mock:
    """Provide mocked Request with valid X-API-Key header."""
    request = Mock(spec=Request)
    request.headers = Mock()
    request.headers.get = Mock(return_value="sk_test_valid_key")
    return request


@pytest.fixture
def mock_request_without_api_key() -> Mock:
    """Provide mocked Request without X-API-Key header."""
    request = Mock(spec=Request)
    request.headers = Mock()
    request.headers.get = Mock(return_value=None)
    return request


class TestAPIKeyProviderInitialization:
    """Test suite for APIKeyProvider initialization."""

    def test_creates_provider_with_default_header_name(
        self, mock_get_api_key_service: Mock
    ) -> None:
        """Test provider creation with default X-API-Key header."""
        provider = APIKeyProvider(get_api_key_service=mock_get_api_key_service)

        assert provider._header_name == "X-API-Key"
        assert provider.name == "api_key"

    def test_creates_provider_with_custom_header_name(
        self, mock_get_api_key_service: Mock
    ) -> None:
        """Test provider creation with custom header name."""
        provider = APIKeyProvider(
            get_api_key_service=mock_get_api_key_service,
            header_name="Custom-API-Key",
        )

        assert provider._header_name == "Custom-API-Key"


class TestCanAuthenticate:
    """Test suite for request authentication capability check."""

    def test_can_authenticate_returns_true_when_header_present(
        self,
        api_key_provider: APIKeyProvider,
        mock_request_with_api_key: Mock,
    ) -> None:
        """Test can_authenticate returns True when X-API-Key header is present."""
        result = api_key_provider.can_authenticate(mock_request_with_api_key)

        assert result is True

    def test_can_authenticate_returns_false_when_header_missing(
        self,
        api_key_provider: APIKeyProvider,
        mock_request_without_api_key: Mock,
    ) -> None:
        """Test can_authenticate returns False when X-API-Key header is missing."""
        result = api_key_provider.can_authenticate(mock_request_without_api_key)

        assert result is False

    def test_can_authenticate_uses_configured_header_name(
        self, mock_get_api_key_service: Mock
    ) -> None:
        """Test can_authenticate checks the configured header name."""
        provider = APIKeyProvider(
            get_api_key_service=mock_get_api_key_service,
            header_name="Custom-Key",
        )
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(
            side_effect=lambda h: "value" if h == "Custom-Key" else None
        )

        result = provider.can_authenticate(request)

        assert result is True
        request.headers.get.assert_called_with("Custom-Key")


class TestAuthenticate:
    """Test suite for full authentication flow."""

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_when_header_missing(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None when API key header is missing."""
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value=None)

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_when_service_not_in_state(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None when api_key_service not in request.state."""
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_test_key")
        request.state = Mock(spec=[])  # No api_key_service attribute

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_user_for_valid_key(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
        sample_user: User,
    ) -> None:
        """Test authenticate returns user for valid API key."""
        mock_api_key_service = AsyncMock(spec=APIKeyService)
        mock_api_key_service.validate_key = AsyncMock(return_value=(sample_user.id, 1))

        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_valid_key")
        request.state = Mock()
        request.state.api_key_service = mock_api_key_service

        mock_user_service.get_by_id = AsyncMock(return_value=sample_user)

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result == sample_user
        mock_api_key_service.validate_key.assert_called_once_with("sk_valid_key")

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_for_invalid_key(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None for invalid API key."""
        mock_api_key_service = AsyncMock(spec=APIKeyService)
        mock_api_key_service.validate_key = AsyncMock(side_effect=InvalidAPIKeyError())

        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_invalid_key")
        request.state = Mock()
        request.state.api_key_service = mock_api_key_service

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_for_expired_key(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None for expired API key."""
        mock_api_key_service = AsyncMock(spec=APIKeyService)
        mock_api_key_service.validate_key = AsyncMock(
            side_effect=APIKeyExpiredError(key_id=1)
        )

        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_expired_key")
        request.state = Mock()
        request.state.api_key_service = mock_api_key_service

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_when_user_not_found(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None when user doesn't exist."""
        mock_api_key_service = AsyncMock(spec=APIKeyService)
        mock_api_key_service.validate_key = AsyncMock(return_value=(999, 1))

        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_valid_key")
        request.state = Mock()
        request.state.api_key_service = mock_api_key_service

        mock_user_service.get_by_id = AsyncMock(side_effect=UserNotFoundError())

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_when_user_inactive(
        self,
        api_key_provider: APIKeyProvider,
        mock_user_service: AsyncMock,
        inactive_user: User,
    ) -> None:
        """Test authenticate returns None when user is inactive."""
        mock_api_key_service = AsyncMock(spec=APIKeyService)
        mock_api_key_service.validate_key = AsyncMock(
            return_value=(inactive_user.id, 1)
        )

        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="sk_valid_key")
        request.state = Mock()
        request.state.api_key_service = mock_api_key_service

        mock_user_service.get_by_id = AsyncMock(return_value=inactive_user)

        result = await api_key_provider.authenticate(request, mock_user_service)

        assert result is None


class TestSecurityScheme:
    """Test suite for security scheme configuration."""

    def test_get_security_scheme_returns_api_key_header(
        self,
        api_key_provider: APIKeyProvider,
    ) -> None:
        """Test get_security_scheme returns APIKeyHeader instance."""
        scheme = api_key_provider.get_security_scheme()

        assert isinstance(scheme, APIKeyHeader)

    def test_get_security_scheme_uses_configured_header_name(
        self, mock_get_api_key_service: Mock
    ) -> None:
        """Test security scheme uses the configured header name."""
        provider = APIKeyProvider(
            get_api_key_service=mock_get_api_key_service,
            header_name="Custom-API-Key",
        )
        scheme = provider.get_security_scheme()

        assert scheme.model.name == "Custom-API-Key"  # type: ignore[attr-defined]


class TestRouterGeneration:
    """Test suite for router generation."""

    def test_get_router_returns_api_router(
        self,
        api_key_provider: APIKeyProvider,
    ) -> None:
        """Test get_router returns APIRouter instance."""
        router = api_key_provider.get_router()

        assert isinstance(router, APIRouter)

    def test_get_router_has_api_keys_prefix(
        self,
        api_key_provider: APIKeyProvider,
    ) -> None:
        """Test router has correct prefix."""
        router = api_key_provider.get_router()

        assert router.prefix == "/api-keys"
