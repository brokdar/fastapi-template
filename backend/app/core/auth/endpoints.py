"""Authentication API endpoints.

This module defines REST API endpoints for authentication operations including
login and token refresh.
"""

import structlog
from fastapi import status
from fastapi.routing import APIRouter

from app.core.auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.core.exceptions.schemas import (
    ErrorResponse,
    InternalServerErrorResponse,
    ValidationErrorResponse,
)
from app.dependencies import AuthServiceDependency

router = APIRouter(prefix="/auth", tags=["auth"])

logger = structlog.get_logger("auth.endpoints")


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with username/email and password, returns JWT tokens",
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {
            "model": ErrorResponse,
            "description": "Invalid credentials or inactive account",
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid request data",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def login(
    credentials: LoginRequest,
    auth_service: AuthServiceDependency,
) -> TokenResponse:
    """Authenticate user and issue JWT tokens.

    Accepts either username or email along with password. Returns access and
    refresh tokens upon successful authentication.

    Args:
        credentials: Login credentials (username/email + password).
        auth_service: Injected authentication service.

    Returns:
        TokenResponse: Access and refresh JWT tokens.

    Raises:
        InvalidCredentialsError: If credentials are invalid.
        InactiveUserError: If user account is inactive.
    """
    return await auth_service.login(
        username_or_email=credentials.username_or_email,
        password=credentials.password.get_secret_value(),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens",
    description="Exchange refresh token for new access and refresh token pair",
    responses={
        200: {"description": "Tokens refreshed successfully"},
        401: {
            "model": ErrorResponse,
            "description": "Invalid or expired refresh token",
        },
        403: {
            "model": ErrorResponse,
            "description": "User account is inactive",
        },
        404: {
            "model": ErrorResponse,
            "description": "User not found",
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Invalid request data",
        },
        500: {
            "model": InternalServerErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def refresh_tokens(
    refresh_request: RefreshRequest,
    auth_service: AuthServiceDependency,
) -> TokenResponse:
    """Refresh JWT tokens using a valid refresh token.

    Issues a new access and refresh token pair. The old refresh token is
    invalidated (token rotation).

    Args:
        refresh_request: Request containing the refresh token.
        auth_service: Injected authentication service.

    Returns:
        TokenResponse: New access and refresh JWT tokens.

    Raises:
        InvalidTokenError: If refresh token is invalid.
        TokenExpiredError: If refresh token has expired.
        UserNotFoundError: If user no longer exists.
        InactiveUserError: If user account is inactive.
    """
    return await auth_service.refresh_tokens(refresh_request.refresh_token)
