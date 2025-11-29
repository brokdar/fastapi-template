"""Test suite for AuthService orchestration layer."""

from collections.abc import Callable
from inspect import Parameter
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import APIRouter, Request
from fastapi.security.base import SecurityBase

from app.core.auth.exceptions import InvalidTokenError
from app.core.auth.services import AuthService
from app.core.exceptions import AuthorizationError
from app.domains.users.models import User, UserRole
from app.domains.users.services import UserService


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
        auth_service: AuthService,
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
        auth_service: AuthService,
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
        auth_service: AuthService,
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
        auth_service: AuthService,
    ) -> None:
        """Test that require_roles method returns callable."""
        dependency = auth_service.require_roles(UserRole.USER)

        assert callable(dependency)

    @pytest.mark.asyncio
    async def test_dependency_authorizes_user_with_correct_role(
        self,
        auth_service: AuthService,
        regular_user: User,
    ) -> None:
        """Test dependency authorizes user with matching role."""
        dependency = auth_service.require_roles(UserRole.USER)

        result = await dependency(user=regular_user)

        assert result == regular_user

    @pytest.mark.asyncio
    async def test_dependency_allows_user_with_one_of_multiple_required_roles(
        self,
        auth_service: AuthService,
        admin_user: User,
    ) -> None:
        """Test dependency allows user with one of multiple required roles."""
        dependency = auth_service.require_roles(UserRole.USER, UserRole.ADMIN)

        result = await dependency(user=admin_user)

        assert result == admin_user

    @pytest.mark.asyncio
    async def test_raises_authorization_error_when_user_lacks_required_role(
        self,
        auth_service: AuthService,
        regular_user: User,
    ) -> None:
        """Test AuthorizationError when user lacks required role."""
        dependency = auth_service.require_roles(UserRole.ADMIN)

        with pytest.raises(
            AuthorizationError,
            match="User role 'user' not authorized. Required roles: admin",
        ):
            await dependency(user=regular_user)


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
        auth_service: AuthService,
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


class TestAuthServiceGetDependencySignature:
    """Test suite for AuthService._dependency_signature property."""

    def test_returns_signature_with_no_providers(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
    ) -> None:
        """Test signature generation with empty provider list."""
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 2
        assert list(sig.parameters.keys()) == ["request", "user_service"]
        assert sig.return_annotation is User

    def test_returns_signature_with_single_provider(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test signature generation with single provider."""
        provider = create_auth_provider(name="jwt")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 3
        assert list(sig.parameters.keys()) == ["request", "token_jwt", "user_service"]
        token_param = sig.parameters["token_jwt"]
        assert token_param.annotation == str | None
        assert type(token_param.default).__name__ == "Depends"
        assert token_param.kind == Parameter.POSITIONAL_OR_KEYWORD
        assert token_param.default.dependency == provider.get_security_scheme()

    def test_returns_signature_with_multiple_unique_providers(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test signature generation with multiple unique providers."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="api_key")
        provider3 = create_auth_provider(name="oauth2")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 5
        assert list(sig.parameters.keys()) == [
            "request",
            "token_jwt",
            "token_api_key",
            "token_oauth2",
            "user_service",
        ]
        assert (
            sig.parameters["token_jwt"].default.dependency
            == provider1.get_security_scheme()
        )
        assert (
            sig.parameters["token_api_key"].default.dependency
            == provider2.get_security_scheme()
        )
        assert (
            sig.parameters["token_oauth2"].default.dependency
            == provider3.get_security_scheme()
        )
        for param_name in ["token_jwt", "token_api_key", "token_oauth2"]:
            param = sig.parameters[param_name]
            assert param.annotation == str | None
            assert type(param.default).__name__ == "Depends"

    def test_handles_provider_name_with_underscores(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test parameter naming with underscores in provider name."""
        provider = create_auth_provider(name="jwt_bearer")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )

        sig = auth_service._dependency_signature

        assert "token_jwt_bearer" in sig.parameters
        assert sig.parameters["token_jwt_bearer"].annotation == str | None
        assert (
            sig.parameters["token_jwt_bearer"].default.dependency
            == provider.get_security_scheme()
        )

    def test_appends_counter_for_duplicate_provider_names(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test duplicate detection with counter appending."""
        scheme1 = Mock(spec=SecurityBase, name="jwt_scheme_1")
        scheme2 = Mock(spec=SecurityBase, name="jwt_scheme_2")
        provider1 = create_auth_provider(name="jwt", security_scheme=scheme1)
        provider2 = create_auth_provider(name="jwt", security_scheme=scheme2)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 4
        assert list(sig.parameters.keys()) == [
            "request",
            "token_jwt",
            "token_jwt_1",
            "user_service",
        ]
        assert sig.parameters["token_jwt"].default.dependency == scheme1
        assert sig.parameters["token_jwt_1"].default.dependency == scheme2

    def test_increments_counter_for_three_duplicate_providers(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test counter increments correctly for multiple duplicates."""
        scheme1 = Mock(spec=SecurityBase, name="oauth2_scheme_1")
        scheme2 = Mock(spec=SecurityBase, name="oauth2_scheme_2")
        scheme3 = Mock(spec=SecurityBase, name="oauth2_scheme_3")
        provider1 = create_auth_provider(name="oauth2", security_scheme=scheme1)
        provider2 = create_auth_provider(name="oauth2", security_scheme=scheme2)
        provider3 = create_auth_provider(name="oauth2", security_scheme=scheme3)
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 5
        assert list(sig.parameters.keys()) == [
            "request",
            "token_oauth2",
            "token_oauth2_1",
            "token_oauth2_2",
            "user_service",
        ]
        assert sig.parameters["token_oauth2"].default.dependency == scheme1
        assert sig.parameters["token_oauth2_1"].default.dependency == scheme2
        assert sig.parameters["token_oauth2_2"].default.dependency == scheme3

    def test_counter_only_applied_to_duplicate_names(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test counter only appended where duplicates exist."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="jwt")
        provider3 = create_auth_provider(name="api_key")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 5
        assert list(sig.parameters.keys()) == [
            "request",
            "token_jwt",
            "token_jwt_1",
            "token_api_key",
            "user_service",
        ]
        assert "token_api_key_1" not in sig.parameters

    def test_detects_duplicates_in_any_provider_order(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test duplicate detection works across non-consecutive providers."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="oauth2")
        provider3 = create_auth_provider(name="oauth2")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 5
        assert list(sig.parameters.keys()) == [
            "request",
            "token_jwt",
            "token_oauth2",
            "token_oauth2_1",
            "user_service",
        ]

    def test_handles_complex_interleaved_duplicate_pattern(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test independent counter tracking for complex duplicate patterns."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="jwt")
        provider3 = create_auth_provider(name="api_key")
        provider4 = create_auth_provider(name="jwt")
        provider5 = create_auth_provider(name="api_key")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2, provider3, provider4, provider5],
        )

        sig = auth_service._dependency_signature

        assert len(sig.parameters) == 7
        assert list(sig.parameters.keys()) == [
            "request",
            "token_jwt",
            "token_jwt_1",
            "token_api_key",
            "token_jwt_2",
            "token_api_key_1",
            "user_service",
        ]

    def test_validates_parameter_types_and_kinds(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test all parameters have correct types and kinds."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="api_key")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )

        sig = auth_service._dependency_signature

        for param in sig.parameters.values():
            assert isinstance(param, Parameter)
            assert param.kind == Parameter.POSITIONAL_OR_KEYWORD

        request_param = sig.parameters["request"]
        assert request_param.default == Parameter.empty

        token_jwt_param = sig.parameters["token_jwt"]
        assert type(token_jwt_param.default).__name__ == "Depends"

        token_api_key_param = sig.parameters["token_api_key"]
        assert type(token_api_key_param.default).__name__ == "Depends"

        user_service_param = sig.parameters["user_service"]
        assert type(user_service_param.default).__name__ == "Depends"

    def test_validates_annotation_types(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test all parameter annotations are correct."""
        provider1 = create_auth_provider(name="jwt")
        provider2 = create_auth_provider(name="api_key")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider1, provider2],
        )

        sig = auth_service._dependency_signature

        assert sig.parameters["request"].annotation is Request
        assert sig.parameters["token_jwt"].annotation == str | None
        assert sig.parameters["token_api_key"].annotation == str | None
        assert sig.parameters["user_service"].annotation is UserService
        assert sig.return_annotation is User

    def test_validates_depends_wrapper(
        self,
        mock_user_service_dependency: Callable[[], AsyncMock],
        create_auth_provider: Callable[..., Mock],
    ) -> None:
        """Test Depends correctly wraps security schemes and callables."""
        provider = create_auth_provider(name="jwt")
        auth_service = AuthService(
            get_user_service=mock_user_service_dependency,
            providers=[provider],
        )

        sig = auth_service._dependency_signature

        token_param = sig.parameters["token_jwt"]
        assert type(token_param.default).__name__ == "Depends"
        assert token_param.default.dependency == provider.get_security_scheme()

        user_service_param = sig.parameters["user_service"]
        assert type(user_service_param.default).__name__ == "Depends"
        assert user_service_param.default.dependency == auth_service.get_user_service
