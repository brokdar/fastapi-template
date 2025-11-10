"""JWT authentication routes for login and token refresh.

This module creates FastAPI router with JWT authentication endpoints.
Types are inferred from dependencies.py configuration.
"""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth.exceptions import InactiveUserError
from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.schemas import RefreshTokenRequest, TokenResponse
from app.dependencies import get_user_service
from app.domains.users.exceptions import InvalidCredentialsError, UserNotFoundError
from app.domains.users.services import UserService

logger = structlog.get_logger("auth.provider.jwt.router")


def create_jwt_router[ID: (int, UUID)](provider: JWTAuthProvider[ID]) -> APIRouter:
    """Create JWT router with provider instance bound via closure.

    The ID type is inferred from the provider parameter. The router uses
    get_user_service from dependencies.py which must return UserService[ID]
    matching the provider's ID type.

    Args:
        provider: JWT authentication provider instance.

    Returns:
        APIRouter containing JWT authentication endpoints.
    """
    router = APIRouter(prefix="/jwt", tags=["Authentication"])

    @router.post(
        "/login",
        response_model=TokenResponse,
        summary="Login with username and password",
        description="Authenticate user credentials and receive access and refresh tokens.",
    )
    async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_service: UserService[ID] = Depends(get_user_service),
    ) -> TokenResponse:
        """Authenticate user and return JWT tokens.

        Validates user credentials and returns both access and refresh tokens
        if authentication is successful.

        Args:
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

        if user.id is None:
            raise InvalidCredentialsError("User ID is None after authentication")

        token_response = provider.create_token_response(str(user.id))

        logger.info(
            "login_successful",
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
    async def refresh(
        request: RefreshTokenRequest,
        user_service: UserService[ID] = Depends(get_user_service),
    ) -> TokenResponse:
        """Refresh access token using refresh token.

        Validates the refresh token and issues new access and refresh tokens.
        Implements token rotation for enhanced security.

        Args:
            request: Refresh token request containing the refresh token.
            user_service: User service implementing authentication operations.

        Returns:
            TokenResponse containing new access and refresh tokens.

        Raises:
            InvalidTokenError: If refresh token is invalid or malformed.
            TokenExpiredError: If refresh token has expired.
            UserNotFoundError: If user from token not found.
            InactiveUserError: If user account is inactive.
        """
        user_id_str = provider.verify_token(
            request.refresh_token, expected_type="refresh"
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

        if user.id is None:
            raise InvalidCredentialsError("User ID is None after token verification")

        token_response = provider.create_token_response(str(user.id))

        logger.info(
            "token_refresh_successful",
            user_id=user.id,
            username=user.username,
        )

        return token_response

    return router
