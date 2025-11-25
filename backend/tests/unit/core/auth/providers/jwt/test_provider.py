"""Test suite for JWT authentication provider."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock

import jwt
import pytest
from fastapi import Request
from fastapi.openapi.models import OAuth2
from fastapi.security import OAuth2PasswordBearer

from app.core.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.schemas import TokenResponse
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import User


class TestJWTAuthProviderInitialization:
    """Test suite for JWTAuthProvider initialization."""

    def test_creates_provider_with_valid_secret_key(self, secret_key: str) -> None:
        """Test successful provider creation with valid configuration."""
        provider = JWTAuthProvider(
            secret_key=secret_key,
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
        )

        assert provider.secret_key == secret_key
        assert provider.algorithm == "HS256"
        assert provider.access_token_expire_minutes == 30
        assert provider.refresh_token_expire_days == 14
        assert provider.name == "jwt"

    def test_raises_value_error_when_secret_key_too_short(self) -> None:
        """Test ValueError is raised when secret key is less than 32 characters."""
        with pytest.raises(
            ValueError, match="JWT secret key must be at least 32 characters"
        ):
            JWTAuthProvider(secret_key="short_key")

    @pytest.mark.parametrize(
        "algorithm",
        ["RS256", "ES256", "PS256", "INVALID"],
        ids=["rsa", "elliptic_curve", "pss", "invalid"],
    )
    def test_raises_value_error_when_algorithm_unsupported(
        self, secret_key: str, algorithm: str
    ) -> None:
        """Test ValueError is raised for unsupported algorithms."""
        with pytest.raises(ValueError, match=f"Unsupported algorithm: {algorithm}"):
            JWTAuthProvider(secret_key=secret_key, algorithm=algorithm)

    @pytest.mark.parametrize(
        "algorithm",
        ["HS256", "HS384", "HS512"],
        ids=["hs256", "hs384", "hs512"],
    )
    def test_creates_provider_with_supported_algorithms(
        self, secret_key: str, algorithm: str
    ) -> None:
        """Test provider creation with all supported HMAC algorithms."""
        provider = JWTAuthProvider(secret_key=secret_key, algorithm=algorithm)

        assert provider.algorithm == algorithm

    def test_sets_default_expiration_times(self, secret_key: str) -> None:
        """Test provider uses default expiration values when not specified."""
        provider = JWTAuthProvider(secret_key=secret_key)

        assert provider.access_token_expire_minutes == 15
        assert provider.refresh_token_expire_days == 7

    def test_sets_custom_expiration_times(self, secret_key: str) -> None:
        """Test provider accepts custom expiration values."""
        provider = JWTAuthProvider(
            secret_key=secret_key,
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
        )

        assert provider.access_token_expire_minutes == 60
        assert provider.refresh_token_expire_days == 30


class TestTokenCreation:
    """Test suite for JWT token creation methods."""

    def test_create_access_token_returns_valid_jwt(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test access token creation returns decodable JWT."""
        token = jwt_provider.create_access_token("123")

        assert isinstance(token, str)
        assert len(token.split(".")) == 3

        payload = jwt.decode(
            token, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_create_refresh_token_returns_valid_jwt(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test refresh token creation returns decodable JWT."""
        token = jwt_provider.create_refresh_token("456")

        assert isinstance(token, str)
        payload = jwt.decode(
            token, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        assert payload["sub"] == "456"
        assert payload["type"] == "refresh"

    def test_creates_access_token_with_correct_expiration(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test access token expiration is set correctly."""
        now = datetime.now(UTC)
        token = jwt_provider.create_access_token("1")

        payload = jwt.decode(
            token, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        token_exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp = now + timedelta(minutes=jwt_provider.access_token_expire_minutes)

        time_diff = abs((token_exp - expected_exp).total_seconds())
        assert time_diff < 2

    def test_creates_refresh_token_with_correct_expiration(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test refresh token expiration is set correctly."""
        now = datetime.now(UTC)
        token = jwt_provider.create_refresh_token("1")

        payload = jwt.decode(
            token, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        token_exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected_exp = now + timedelta(days=jwt_provider.refresh_token_expire_days)

        time_diff = abs((token_exp - expected_exp).total_seconds())
        assert time_diff < 2

    def test_creates_token_with_required_claims(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test token includes all required RFC 7519 claims."""
        token = jwt_provider.create_access_token("1")

        payload = jwt.decode(
            token, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload

    def test_creates_token_with_different_user_ids(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test tokens can be created for different user IDs."""
        token1 = jwt_provider.create_access_token("100")
        token2 = jwt_provider.create_access_token("200")

        payload1 = jwt.decode(
            token1, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )
        payload2 = jwt.decode(
            token2, jwt_provider.secret_key, algorithms=[jwt_provider.algorithm]
        )

        assert payload1["sub"] == "100"
        assert payload2["sub"] == "200"


class TestTokenResponse:
    """Test suite for token response creation."""

    def test_create_token_response_includes_both_tokens(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test token response contains access and refresh tokens."""
        response = jwt_provider.create_token_response("1")

        assert isinstance(response, TokenResponse)
        assert response.access_token
        assert response.refresh_token
        assert response.access_token != response.refresh_token

    def test_create_token_response_has_correct_structure(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test token response follows OAuth2 specification."""
        response = jwt_provider.create_token_response("1")

        assert response.token_type == "bearer"
        assert response.expires_in > 0
        assert isinstance(response.access_token, str)
        assert isinstance(response.refresh_token, str)

    def test_create_token_response_calculates_expires_in_correctly(
        self, jwt_provider: JWTAuthProvider
    ) -> None:
        """Test expires_in field matches access token expiration."""
        response = jwt_provider.create_token_response("1")

        expected_expires_in = jwt_provider.access_token_expire_minutes * 60
        assert response.expires_in == expected_expires_in


class TestTokenVerification:
    """Test suite for JWT token verification."""

    def test_verify_token_returns_user_id_for_valid_access_token(
        self,
        jwt_provider: JWTAuthProvider,
        valid_access_token: str,
    ) -> None:
        """Test verification returns user ID for valid token."""
        user_id = jwt_provider.verify_token(valid_access_token, expected_type="access")

        assert user_id == "1"

    def test_verify_token_returns_user_id_for_valid_refresh_token(
        self,
        jwt_provider: JWTAuthProvider,
        valid_refresh_token: str,
    ) -> None:
        """Test verification returns user ID for valid refresh token."""
        user_id = jwt_provider.verify_token(
            valid_refresh_token, expected_type="refresh"
        )

        assert user_id == "1"

    def test_raises_token_expired_error_when_token_expired(
        self,
        jwt_provider: JWTAuthProvider,
        expired_token: str,
    ) -> None:
        """Test TokenExpiredError is raised for expired token."""
        with pytest.raises(TokenExpiredError, match="Token has expired"):
            jwt_provider.verify_token(expired_token, expected_type="access")

    def test_raises_invalid_token_error_when_token_malformed(
        self,
        jwt_provider: JWTAuthProvider,
        malformed_token: str,
    ) -> None:
        """Test InvalidTokenError is raised for malformed token."""
        with pytest.raises(InvalidTokenError, match="Invalid token"):
            jwt_provider.verify_token(malformed_token, expected_type="access")

    def test_raises_invalid_token_error_when_signature_invalid(
        self,
        jwt_provider: JWTAuthProvider,
        token_with_invalid_signature: str,
    ) -> None:
        """Test InvalidTokenError is raised for invalid signature."""
        with pytest.raises(InvalidTokenError, match="Invalid token"):
            jwt_provider.verify_token(
                token_with_invalid_signature, expected_type="access"
            )

    def test_raises_invalid_token_error_when_token_type_mismatch(
        self,
        jwt_provider: JWTAuthProvider,
        valid_access_token: str,
    ) -> None:
        """Test InvalidTokenError is raised when token type doesn't match expected."""
        with pytest.raises(
            InvalidTokenError, match="Invalid token type: expected refresh, got access"
        ):
            jwt_provider.verify_token(valid_access_token, expected_type="refresh")

    def test_raises_invalid_token_error_when_required_claims_missing(
        self,
        jwt_provider: JWTAuthProvider,
        secret_key: str,
    ) -> None:
        """Test InvalidTokenError is raised when required claims are missing."""
        payload: dict[str, Any] = {"sub": "1"}
        token = jwt.encode(payload, secret_key, algorithm="HS256")

        with pytest.raises(InvalidTokenError, match="Invalid token"):
            jwt_provider.verify_token(token, expected_type="access")

    @pytest.mark.parametrize(
        "algorithm",
        ["HS256", "HS384", "HS512"],
        ids=["hs256", "hs384", "hs512"],
    )
    def test_verify_token_with_different_algorithms(
        self, secret_key: str, algorithm: str
    ) -> None:
        """Test token verification works with all supported algorithms."""
        provider = JWTAuthProvider(secret_key=secret_key, algorithm=algorithm)
        token = provider.create_access_token("1")

        user_id = provider.verify_token(token, expected_type="access")

        assert user_id == "1"


class TestCanAuthenticate:
    """Test suite for request authentication capability check."""

    def test_can_authenticate_returns_true_for_bearer_token(
        self,
        jwt_provider: JWTAuthProvider,
        mock_request_with_bearer_token: Mock,
    ) -> None:
        """Test can_authenticate returns True for valid Bearer token."""
        result = jwt_provider.can_authenticate(mock_request_with_bearer_token)

        assert result is True

    def test_can_authenticate_returns_false_for_missing_header(
        self,
        jwt_provider: JWTAuthProvider,
        mock_request_without_token: Mock,
    ) -> None:
        """Test can_authenticate returns False when Authorization header is missing."""
        result = jwt_provider.can_authenticate(mock_request_without_token)

        assert result is False

    @pytest.mark.parametrize(
        "auth_header",
        ["Basic dXNlcjpwYXNz", "Token abc123", "Bearer", ""],
        ids=["basic_auth", "token_auth", "bearer_only", "empty"],
    )
    def test_can_authenticate_returns_false_for_invalid_format(
        self,
        jwt_provider: JWTAuthProvider,
        auth_header: str,
    ) -> None:
        """Test can_authenticate returns False for various invalid formats."""
        request = Mock(spec=Request)
        request.headers.get.return_value = auth_header

        result = jwt_provider.can_authenticate(request)

        assert result is False


class TestAuthenticate:
    """Test suite for full authentication flow."""

    @pytest.mark.asyncio
    async def test_authenticate_returns_user_for_valid_token(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
        sample_user: User,
    ) -> None:
        """Test authenticate returns user for valid token."""
        token = jwt_provider.create_access_token(str(sample_user.id))
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {token}"

        mock_user_service.get_by_id.return_value = sample_user

        result = await jwt_provider.authenticate(request, mock_user_service)

        assert result == sample_user
        mock_user_service.get_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_for_missing_token(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
        mock_request_without_token: Mock,
    ) -> None:
        """Test authenticate returns None when token is missing."""
        result = await jwt_provider.authenticate(
            mock_request_without_token, mock_user_service
        )

        assert result is None
        mock_user_service.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_for_invalid_token(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
        malformed_token: str,
    ) -> None:
        """Test authenticate returns None for invalid token."""
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {malformed_token}"

        result = await jwt_provider.authenticate(request, mock_user_service)

        assert result is None
        mock_user_service.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_for_expired_token(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
        expired_token: str,
    ) -> None:
        """Test authenticate returns None for expired token."""
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {expired_token}"

        result = await jwt_provider.authenticate(request, mock_user_service)

        assert result is None
        mock_user_service.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_invalid_token_error_when_user_id_invalid(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test InvalidTokenError is raised when user ID cannot be parsed."""
        token = jwt_provider.create_access_token("invalid_id")
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {token}"

        with pytest.raises(
            InvalidTokenError, match="Invalid user ID in token: 'invalid_id'"
        ):
            await jwt_provider.authenticate(request, mock_user_service)

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
    ) -> None:
        """Test authenticate returns None when user doesn't exist."""
        token = jwt_provider.create_access_token("999")
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {token}"

        mock_user_service.get_by_id.side_effect = UserNotFoundError("User not found")

        result = await jwt_provider.authenticate(request, mock_user_service)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_inactive(
        self,
        jwt_provider: JWTAuthProvider,
        mock_user_service: AsyncMock,
        inactive_user: User,
    ) -> None:
        """Test authenticate returns None when user account is inactive."""
        token = jwt_provider.create_access_token(str(inactive_user.id))
        request = Mock(spec=Request)
        request.headers.get.return_value = f"Bearer {token}"

        mock_user_service.get_by_id.return_value = inactive_user

        result = await jwt_provider.authenticate(request, mock_user_service)

        assert result is None


class TestSecurityScheme:
    """Test suite for security scheme configuration."""

    def test_get_security_scheme_returns_oauth2_password_bearer(
        self,
        jwt_provider: JWTAuthProvider,
    ) -> None:
        """Test get_security_scheme returns OAuth2PasswordBearer instance."""
        scheme = jwt_provider.get_security_scheme()

        assert isinstance(scheme, OAuth2PasswordBearer)

    def test_get_security_scheme_has_correct_token_url(
        self,
        jwt_provider: JWTAuthProvider,
    ) -> None:
        """Test security scheme has correct token URL for OpenAPI."""
        scheme = jwt_provider.get_security_scheme()

        assert isinstance(scheme.model, OAuth2)
        assert scheme.model.flows.password is not None
        assert scheme.model.flows.password.tokenUrl == "/auth/jwt/login"


class TestRouterGeneration:
    """Test suite for router generation."""

    def test_get_router_returns_api_router(self, jwt_provider: JWTAuthProvider) -> None:
        """Test get_router returns APIRouter instance."""
        from fastapi import APIRouter

        router = jwt_provider.get_router()

        assert isinstance(router, APIRouter)

    def test_get_router_has_jwt_prefix(self, jwt_provider: JWTAuthProvider) -> None:
        """Test router has correct prefix."""
        router = jwt_provider.get_router()

        assert router.prefix == "/jwt"
