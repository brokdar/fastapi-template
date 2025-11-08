"""Multi-provider authentication module."""

from app.core.auth.config import AuthSettings
from app.core.auth.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.jwt import (
    JWTAuthProvider,
    JWTAuthService,
    LoginRequest,
    RefreshRequest,
    TokenPayload,
    TokenResponse,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.auth.services import AuthService

__all__ = [
    "AuthProvider",
    "AuthService",
    "AuthSettings",
    "JWTAuthProvider",
    "JWTAuthService",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "InvalidTokenError",
    "TokenExpiredError",
    "InactiveUserError",
    "InsufficientPermissionsError",
]
