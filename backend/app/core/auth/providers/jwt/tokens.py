"""JWT token creation and verification module."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pydantic import ValidationError

from app.core.auth.exceptions import InvalidTokenError, TokenExpiredError
from app.core.auth.providers.jwt.schemas import TokenPayload
from app.domains.users.models import UserRole


def create_access_token(
    user_id: int,
    username: str,
    role: UserRole,
    secret_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 15,
) -> str:
    """Create a new JWT access token.

    Args:
        user_id: User's unique identifier.
        username: Username of the user.
        role: User's role for authorization.
        secret_key: Secret key for JWT signing.
        algorithm: JWT signing algorithm (default: HS256).
        expire_minutes: Token expiration time in minutes (default: 15).

    Returns:
        str: Encoded JWT access token.
    """
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=expire_minutes)

    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def create_refresh_token(
    user_id: int,
    secret_key: str,
    algorithm: str = "HS256",
    expire_days: int = 7,
) -> str:
    """Create a new JWT refresh token.

    Args:
        user_id: User's unique identifier.
        secret_key: Secret key for JWT signing.
        algorithm: JWT signing algorithm (default: HS256).
        expire_days: Token expiration time in days (default: 7).

    Returns:
        str: Encoded JWT refresh token.
    """
    now = datetime.now(UTC)
    expires = now + timedelta(days=expire_days)

    payload = {
        "sub": user_id,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }

    return jwt.encode(payload, secret_key, algorithm=algorithm)


def verify_token(
    token: str,
    token_type: Literal["access", "refresh"],
    secret_key: str,
    algorithm: str = "HS256",
) -> TokenPayload:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify.
        token_type: Expected token type ("access" or "refresh").
        secret_key: Secret key for JWT verification.
        algorithm: JWT signing algorithm (default: HS256).

    Returns:
        TokenPayload: Validated token payload.

    Raises:
        TokenExpiredError: If token has expired.
        InvalidTokenError: If token is invalid or malformed.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])

        if payload.get("type") != token_type:
            raise InvalidTokenError(
                f"Invalid token type: expected {token_type}, got {payload.get('type')}"
            )

        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError() from e
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError("Invalid or malformed token") from e
    except ValidationError as e:
        raise InvalidTokenError(f"Token validation failed: {e}") from e
