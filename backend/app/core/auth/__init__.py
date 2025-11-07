"""Authentication module for JWT-based authentication and authorization."""

from app.core.auth.dependencies import (
    OptionalUserDependency,
    RequiresUserDependency,
    get_current_user,
    get_optional_user,
    require_role,
)
from app.core.auth.exceptions import (
    InactiveUserError,
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.auth.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.core.auth.services import AuthService
from app.core.auth.tokens import (
    create_access_token,
    create_refresh_token,
    verify_token,
)

__all__ = [
    "AuthService",
    "LoginRequest",
    "RefreshRequest",
    "TokenResponse",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "get_current_user",
    "get_optional_user",
    "RequiresUserDependency",
    "OptionalUserDependency",
    "require_role",
    "InvalidTokenError",
    "TokenExpiredError",
    "InactiveUserError",
    "InsufficientPermissionsError",
]
