"""JWT authentication provider implementation.

This module implements RFC 7519-compliant JWT authentication with access and
refresh token support, including token rotation for enhanced security.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
import structlog
from fastapi import APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.base import SecurityBase

from app.core.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.auth.protocols import AuthenticationUserService
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.jwt.schemas import TokenPayload, TokenResponse
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import User

logger = structlog.get_logger("auth.provider.jwt")


class JWTAuthProvider[ID: (int, UUID)](AuthProvider[ID]):
    """JWT authentication provider implementing RFC 7519 specification.

    Provides stateless authentication using JSON Web Tokens with support for
    access and refresh tokens. Implements token rotation on refresh for
    enhanced security.

    Attributes:
        name: Provider identifier.
        secret_key: Secret key for token signing and verification.
        algorithm: JWT signing algorithm (default: HS256).
        access_token_expire_minutes: Access token lifetime in minutes.
        refresh_token_expire_days: Refresh token lifetime in days.
    """

    name = "jwt"

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ) -> None:
        """Initialize JWT authentication provider.

        Args:
            secret_key: Secret key for signing tokens (minimum 32 characters).
            algorithm: JWT signing algorithm (must be HS256 for RFC compliance).
            access_token_expire_minutes: Access token expiration in minutes.
            refresh_token_expire_days: Refresh token expiration in days.

        Raises:
            ValueError: If secret_key is too short or algorithm is not supported.
        """
        if len(secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        if algorithm not in ["HS256", "HS384", "HS512"]:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def _create_token(
        self, user_id: str, token_type: str, expire_delta: timedelta
    ) -> str:
        """Create JWT token with standard RFC 7519 claims.

        Args:
            user_id: User identifier for sub claim.
            token_type: Token type for type claim ("access" or "refresh").
            expire_delta: Time until expiration.

        Returns:
            Encoded JWT token string.
        """
        now = datetime.now(UTC)
        expire = now + expire_delta

        payload: dict[str, Any] = {
            "sub": user_id,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": token_type,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, user_id: str) -> str:
        """Create RFC 7519-compliant access token.

        Generates a JWT with the following claims:
        - sub: User ID (subject)
        - exp: Expiration time (NumericDate)
        - iat: Issued at time (NumericDate)
        - type: Token type ("access")

        Args:
            user_id: String representation of user identifier to encode in token.

        Returns:
            Encoded JWT access token string.
        """
        token = self._create_token(
            user_id, "access", timedelta(minutes=self.access_token_expire_minutes)
        )
        logger.debug(
            "access_token_created",
            user_id=user_id,
            expires_in_minutes=self.access_token_expire_minutes,
        )
        return token

    def create_refresh_token(self, user_id: str) -> str:
        """Create RFC 7519-compliant refresh token.

        Generates a JWT with the following claims:
        - sub: User ID (subject)
        - exp: Expiration time (NumericDate)
        - iat: Issued at time (NumericDate)
        - type: Token type ("refresh")

        Args:
            user_id: String representation of user identifier to encode in token.

        Returns:
            Encoded JWT refresh token string.
        """
        token = self._create_token(
            user_id, "refresh", timedelta(days=self.refresh_token_expire_days)
        )
        logger.debug(
            "refresh_token_created",
            user_id=user_id,
            expires_in_days=self.refresh_token_expire_days,
        )
        return token

    def create_token_response(self, user_id: str) -> TokenResponse:
        """Create complete token response with access and refresh tokens.

        Args:
            user_id: String representation of user identifier for token generation.

        Returns:
            TokenResponse containing both access and refresh tokens.
        """
        access_token = self.create_access_token(user_id)
        refresh_token = self.create_refresh_token(user_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",  # noqa: S106
            expires_in=self.access_token_expire_minutes * 60,
        )

    def verify_token(self, token: str, expected_type: str) -> str:
        """Verify JWT token and extract user ID string with RFC 7519 compliance.

        Performs comprehensive token validation:
        1. Verifies JWT structure (header.payload.signature)
        2. Validates JOSE Header (alg, typ)
        3. Verifies signature using secret key
        4. Validates Claims Set as UTF-8 JSON
        5. Checks expiration time (exp claim)
        6. Validates token type matches expected
        7. Extracts and returns user ID string from sub claim

        Note: Returns string representation of user ID. The calling code
        (authenticate method) is responsible for parsing the string to the
        appropriate typed ID using user_service.parse_id().

        Args:
            token: JWT token string to verify.
            expected_type: Expected token type ("access" or "refresh").

        Returns:
            User ID string extracted from sub claim.

        Raises:
            InvalidTokenError: Token is malformed, invalid signature, or wrong type.
            TokenExpiredError: Token has exceeded its expiration time.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={
                    "require": ["sub", "exp", "iat", "type"],
                    "verify_signature": True,
                    "verify_exp": True,
                },
            )

            token_payload = TokenPayload(**payload)

            if token_payload.type != expected_type:
                logger.warning(
                    "token_type_mismatch",
                    expected=expected_type,
                    actual=token_payload.type,
                )
                raise InvalidTokenError(
                    f"Invalid token type: expected {expected_type}, got {token_payload.type}"
                )

            logger.debug(
                "token_verified",
                user_id=token_payload.sub,
                token_type=expected_type,
            )
            return token_payload.sub

        except jwt.ExpiredSignatureError as e:
            logger.warning("token_expired", error=str(e))
            raise TokenExpiredError("Token has expired") from e

        except jwt.InvalidTokenError as e:
            logger.warning("token_invalid", error=str(e))
            raise InvalidTokenError(f"Invalid token: {e!s}") from e

    def can_authenticate(self, request: Request) -> bool:
        """Check if request contains JWT Bearer token.

        Args:
            request: FastAPI request object.

        Returns:
            True if Authorization header contains Bearer token, False otherwise.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False

        parts = auth_header.split()
        return len(parts) == 2 and parts[0].lower() == "bearer"

    async def authenticate(
        self, request: Request, user_service: AuthenticationUserService[ID]
    ) -> User | None:
        """Authenticate request using JWT access token.

        Extracts and verifies the JWT token from the Authorization header,
        validates the token, parses the user ID, retrieves the user, and
        checks account status.

        Returns None for all authentication failures to allow fallback to
        other providers in multi-provider configurations. This prevents
        leaking information about user existence or account status.

        Args:
            request: FastAPI request object.
            user_service: User service implementing authentication operations.

        Returns:
            Authenticated User object or None if authentication fails
            (invalid token, user not found, or inactive account).

        Raises:
            InvalidTokenError: Token is malformed or has invalid user ID format.
        """
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split()[1] if len(auth_header.split()) == 2 else ""

        if not token:
            logger.warning("authentication_failed", reason="missing_token")
            return None

        try:
            user_id_str = self.verify_token(token, expected_type="access")
        except (InvalidTokenError, TokenExpiredError):
            return None

        try:
            user_id = user_service.parse_id(user_id_str)
        except Exception as e:
            logger.warning(
                "authentication_failed",
                reason="invalid_user_id_in_token",
                user_id_str=user_id_str,
                error=str(e),
            )
            raise InvalidTokenError(f"Invalid user ID in token: {user_id_str!r}") from e

        try:
            user = await user_service.get_by_id(user_id)
        except UserNotFoundError:
            logger.warning(
                "authentication_failed",
                reason="token_refers_to_nonexistent_user",
            )
            return None

        if not user.is_active:
            logger.warning(
                "authentication_failed",
                reason="inactive_user",
            )
            return None

        logger.info(
            "authentication_successful",
            user_id=user.id,
            username=user.username,
        )
        return user

    def get_security_scheme(self) -> SecurityBase:
        """Get FastAPI security scheme for OpenAPI documentation.

        Returns:
            OAuth2PasswordBearer security scheme.
        """
        return OAuth2PasswordBearer(tokenUrl="/auth/jwt/login")

    def get_router(self) -> APIRouter:
        """Get FastAPI router with authentication endpoints.

        Creates a new router instance with this provider bound via closure.
        Uses lazy import to avoid circular dependency at module level.

        Returns:
            APIRouter containing /login and /refresh endpoints.
        """
        from app.core.auth.providers.jwt.router import create_jwt_router

        return create_jwt_router(self)
