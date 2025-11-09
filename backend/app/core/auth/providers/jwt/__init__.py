"""JWT authentication provider module.

This module provides RFC 7519-compliant JWT authentication with support for
access and refresh tokens, including token rotation for enhanced security.
"""

from app.core.auth.providers.jwt.provider import JWTAuthProvider
from app.core.auth.providers.jwt.schemas import (
    RefreshTokenRequest,
    TokenPayload,
    TokenResponse,
)

__all__ = [
    "JWTAuthProvider",
    "TokenResponse",
    "TokenPayload",
    "RefreshTokenRequest",
]
