"""Test suite for AuthService orchestration layer."""

from collections.abc import Callable
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter

from app.core.auth.exceptions import InvalidTokenError
from app.core.auth.services import AuthService
from app.core.exceptions import AuthorizationError
from app.domains.users.models import User, UserRole


class TestAuthServiceAuthenticate:
    """Test suite for AuthService._authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticates_user_with_first_provider(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test successful authentication with first provider."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()

        result = await auth_service._authenticate(mock_request, user_service)

        assert result == regular_user
        provider.can_authenticate.assert_called_once_with(mock_request)
        provider.authenticate.assert_called_once_with(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_authenticates_user_with_second_provider_when_first_cannot(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test authentication falls through to second provider."""
        provider1 = create_auth_provider(name="provider1", can_authenticate=False)
        provider2 = create_auth_provider(
            name="provider2",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )
        user_service = AsyncMock()

        result = await auth_service._authenticate(mock_request, user_service)

        assert result == regular_user
        provider1.can_authenticate.assert_called_once_with(mock_request)
        provider1.authenticate.assert_not_called()
        provider2.can_authenticate.assert_called_once_with(mock_request)
        provider2.authenticate.assert_called_once_with(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_no_provider_can_authenticate(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test InvalidTokenError when no providers can authenticate."""
        provider1 = create_auth_provider(name="provider1", can_authenticate=False)
        provider2 = create_auth_provider(name="provider2", can_authenticate=False)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )
        user_service = AsyncMock()

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await auth_service._authenticate(mock_request, user_service)

        provider1.can_authenticate.assert_called_once_with(mock_request)
        provider2.can_authenticate.assert_called_once_with(mock_request)
        provider1.authenticate.assert_not_called()
        provider2.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_provider_returns_none(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test InvalidTokenError when provider authenticates but returns None."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=None,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await auth_service._authenticate(mock_request, user_service)

        provider.can_authenticate.assert_called_once_with(mock_request)
        provider.authenticate.assert_called_once_with(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_all_providers_return_none(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test InvalidTokenError when multiple providers authenticate but all return None."""
        provider1 = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=None,
        )
        provider2 = create_auth_provider(
            name="provider2",
            can_authenticate=True,
            authenticate_return=None,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )
        user_service = AsyncMock()

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await auth_service._authenticate(mock_request, user_service)

        provider1.authenticate.assert_called_once_with(mock_request, user_service)
        provider2.authenticate.assert_called_once_with(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_with_empty_provider_list(
        self,
        mock_request: Mock,
        auth_service: AuthService[int],
    ) -> None:
        """Test InvalidTokenError when no providers configured."""
        user_service = AsyncMock()

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await auth_service._authenticate(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_skips_remaining_providers_after_successful_authentication(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test that authentication stops after first successful provider."""
        provider1 = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        provider2 = create_auth_provider(name="provider2", can_authenticate=True)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )
        user_service = AsyncMock()

        result = await auth_service._authenticate(mock_request, user_service)

        assert result == regular_user
        provider1.authenticate.assert_called_once()
        provider2.can_authenticate.assert_not_called()
        provider2.authenticate.assert_not_called()


class TestAuthServiceRequireUser:
    """Test suite for AuthService.require_user property."""

    def test_returns_dependency_function(
        self,
        auth_service: AuthService[int],
    ) -> None:
        """Test that require_user property returns callable."""
        dependency = auth_service.require_user

        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_authenticates_user_successfully(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test dependency function authenticates user successfully."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()
        dependency = auth_service.require_user

        result = await dependency(mock_request, user_service)

        assert result == regular_user

    @pytest.mark.asyncio
    async def test_dependency_raises_invalid_token_error_when_authentication_fails(
        self,
        mock_request: Mock,
        auth_service: AuthService[int],
    ) -> None:
        """Test dependency raises InvalidTokenError when authentication fails."""
        user_service = AsyncMock()
        dependency = auth_service.require_user

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await dependency(mock_request, user_service)


class TestAuthServiceRequireRoles:
    """Test suite for AuthService.require_roles method."""

    def test_returns_dependency_function(
        self,
        auth_service: AuthService[int],
    ) -> None:
        """Test that require_roles method returns callable."""
        dependency = auth_service.require_roles(UserRole.USER)

        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_authenticates_and_authorizes_user_with_correct_role(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test dependency authenticates and authorizes user with matching role."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()
        dependency = auth_service.require_roles(UserRole.USER)

        result = await dependency(mock_request, user_service)

        assert result == regular_user

    @pytest.mark.asyncio
    async def test_dependency_allows_user_with_one_of_multiple_required_roles(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        admin_user: User,
    ) -> None:
        """Test dependency allows user with one of multiple required roles."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=admin_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()
        dependency = auth_service.require_roles(UserRole.USER, UserRole.ADMIN)

        result = await dependency(mock_request, user_service)

        assert result == admin_user

    @pytest.mark.asyncio
    async def test_raises_authorization_error_when_user_lacks_required_role(
        self,
        mock_request: Mock,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        regular_user: User,
    ) -> None:
        """Test AuthorizationError when user lacks required role."""
        provider = create_auth_provider(
            name="provider1",
            can_authenticate=True,
            authenticate_return=regular_user,
        )
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )
        user_service = AsyncMock()
        dependency = auth_service.require_roles(UserRole.ADMIN)

        with pytest.raises(
            AuthorizationError,
            match="User role 'user' not authorized. Required roles: admin",
        ):
            await dependency(mock_request, user_service)

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_before_checking_roles(
        self,
        mock_request: Mock,
        auth_service: AuthService[int],
    ) -> None:
        """Test authentication failure occurs before role checking."""
        user_service = AsyncMock()
        dependency = auth_service.require_roles(UserRole.USER)

        with pytest.raises(InvalidTokenError, match="Authentication failed"):
            await dependency(mock_request, user_service)


class TestAuthServiceRegisterRoutes:
    """Test suite for AuthService.register_routes method."""

    def test_registers_routes_from_all_providers(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        mock_fastapi_app: Mock,
    ) -> None:
        """Test routes registered for all providers."""
        router1 = APIRouter()
        router2 = APIRouter()
        provider1 = create_auth_provider(name="provider1", router=router1)
        provider2 = create_auth_provider(name="provider2", router=router2)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )

        auth_service.register_routes(mock_fastapi_app)

        assert mock_fastapi_app.include_router.call_count == 2
        provider1.get_router.assert_called_once()
        provider2.get_router.assert_called_once()

    def test_registers_routes_with_correct_prefix_and_tags(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        mock_fastapi_app: Mock,
    ) -> None:
        """Test routes registered with correct prefix and tags."""
        router = APIRouter()
        provider = create_auth_provider(name="provider1", router=router)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )

        auth_service.register_routes(mock_fastapi_app)

        mock_fastapi_app.include_router.assert_called_once_with(
            router, prefix="/auth", tags=["auth"]
        )

    def test_handles_empty_provider_list(
        self,
        auth_service: AuthService[int],
        mock_fastapi_app: Mock,
    ) -> None:
        """Test register_routes works with no providers."""
        auth_service.register_routes(mock_fastapi_app)

        mock_fastapi_app.include_router.assert_not_called()

    def test_calls_get_router_for_each_provider(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
        mock_fastapi_app: Mock,
    ) -> None:
        """Test get_router called for each provider exactly once."""
        provider1 = create_auth_provider(name="provider1")
        provider2 = create_auth_provider(name="provider2")
        provider3 = create_auth_provider(name="provider3")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3],
        )

        auth_service.register_routes(mock_fastapi_app)

        provider1.get_router.assert_called_once()
        provider2.get_router.assert_called_once()
        provider3.get_router.assert_called_once()
