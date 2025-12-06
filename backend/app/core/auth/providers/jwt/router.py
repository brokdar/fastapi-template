"""JWT authentication routes for login, logout, and token refresh.

This module creates FastAPI router with JWT authentication endpoints.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, Security
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth.exceptions import InactiveUserError
from app.core.auth.providers.jwt.config import JWTSettings
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.schemas import (
    LogoutResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.core.ratelimit import limiter
from app.dependencies import auth_service, get_user_service
from app.domains.users.exceptions import InvalidCredentialsError, UserNotFoundError
from app.domains.users.models import User
from app.domains.users.services import UserService

logger = structlog.get_logger("auth.provider.jwt.router")


def create_jwt_router(provider: JWTAuthProvider, settings: JWTSettings) -> APIRouter:
    """Create JWT router with provider instance bound via closure.

    Args:
        provider: JWT authentication provider instance.
        settings: JWT settings for rate limit configuration.

    Returns:
        APIRouter containing JWT authentication endpoints.
    """
    router = APIRouter(prefix="/jwt")

    @router.post(
        "/login",
        response_model=TokenResponse,
        summary="Login with username and password",
        description="Authenticate user credentials and receive access and refresh tokens.",
    )
    @limiter.limit(settings.login_rate_limit)
    async def login(
        request: Request,
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_service: UserService = Depends(get_user_service),
    ) -> TokenResponse:
        """Authenticate user and return JWT tokens.

        Validates user credentials and returns both access and refresh tokens
        if authentication is successful. Rate limited per IP address.

        Args:
            request: FastAPI request object (required for rate limiting).
            form_data: OAuth2 password form containing username and password.
            user_service: User service implementing authentication operations.

        Returns:
            TokenResponse containing access and refresh tokens.

        Raises:
            InvalidCredentialsError: If username or password is incorrect.
            InactiveUserError: If user account is inactive.
        """
        try:
            user = await user_service.get_by_name(form_data.username)
        except UserNotFoundError as e:
            logger.warning(
                "login_failed",
                reason="user_not_found",
                username=form_data.username,
            )
            raise InvalidCredentialsError("Invalid username or password") from e

        password_valid = await user_service.verify_password(user, form_data.password)
        if not password_valid:
            logger.warning(
                "login_failed",
                reason="invalid_password",
                username=form_data.username,
            )
            raise InvalidCredentialsError("Invalid username or password")

        if not user.is_active:
            logger.warning(
                "login_failed",
                reason="inactive_user",
                user_id=user.id,
                username=user.username,
            )
            raise InactiveUserError(user_id=user.id)

        token_response = provider.create_token_response(str(user.id))

        logger.info(
            "user_logged_in",
            user_id=user.id,
            username=user.username,
        )

        return token_response

    @router.post(
        "/refresh",
        response_model=TokenResponse,
        summary="Refresh access token",
        description="Exchange refresh token for new access and refresh tokens (token rotation).",
    )
    @limiter.limit(settings.refresh_rate_limit)
    async def refresh(
        request: Request,
        token_data: RefreshTokenRequest,
        user_service: UserService = Depends(get_user_service),
    ) -> TokenResponse:
        """Refresh access token using refresh token.

        Validates the refresh token and issues new access and refresh tokens.
        Implements token rotation for enhanced security. The old refresh token
        is blacklisted to prevent reuse. Rate limited per IP address.

        Args:
            request: FastAPI request object (required for rate limiting).
            token_data: Refresh token request containing the refresh token.
            user_service: User service implementing authentication operations.

        Returns:
            TokenResponse containing new access and refresh tokens.

        Raises:
            InvalidTokenError: If refresh token is invalid or malformed.
            TokenExpiredError: If refresh token has expired.
            TokenBlacklistedError: If refresh token has been revoked.
            UserNotFoundError: If user from token not found.
            InactiveUserError: If user account is inactive.
        """
        user_id_str = await provider.verify_token(
            token_data.refresh_token, expected_type="refresh"
        )
        user_id = user_service.parse_id(user_id_str)

        user = await user_service.get_by_id(user_id)

        if not user.is_active:
            logger.warning(
                "token_refresh_failed",
                reason="inactive_user",
                user_id=user.id,
            )
            raise InactiveUserError(user_id=user.id)

        await provider.blacklist_token(token_data.refresh_token)
        token_response = provider.create_token_response(str(user.id))

        logger.info(
            "token_refreshed",
            user_id=user.id,
            username=user.username,
        )

        return token_response

    @router.post(
        "/logout",
        response_model=LogoutResponse,
        summary="Logout and invalidate token",
        description="Blacklist the current access token to prevent further use.",
    )
    @limiter.limit(settings.logout_rate_limit)
    async def logout(
        request: Request,
        user: Annotated[User, Security(auth_service.require_user)],
    ) -> LogoutResponse:
        """Logout user by blacklisting current access token.

        Extracts the access token from the Authorization header and adds it
        to the blacklist. The token will be rejected on subsequent requests.
        Rate limited per IP address.

        Args:
            request: FastAPI request object (required for rate limiting).
            user: Authenticated user (validated via require_user dependency).

        Returns:
            LogoutResponse confirming successful logout.
        """
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()
        token = parts[1] if len(parts) == 2 else ""

        if token:
            await provider.blacklist_token(token)
            logger.info(
                "user_logged_out",
                user_id=user.id,
                username=user.username,
            )

        return LogoutResponse()

    return router
