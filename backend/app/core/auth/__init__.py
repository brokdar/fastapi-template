"""Multi-provider authentication module."""

from app.core.auth.config import AuthSettings
from app.core.auth.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.auth.protocols import AuthenticationUserService
from app.core.auth.providers.base import AuthProvider
from app.core.auth.providers.jwt import (
    JWTAuthProvider,
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
)
from app.core.auth.services import AuthService

__all__ = [
    "AuthProvider",
    "AuthService",
    "AuthSettings",
    "AuthenticationUserService",
    "JWTAuthProvider",
    "RefreshTokenRequest",
    "TokenResponse",
    "TokenPayload",
    "InvalidTokenError",
    "TokenExpiredError",
    "InactiveUserError",
    "InsufficientPermissionsError",
]
