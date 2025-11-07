"""JWT token creation and verification module."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pydantic import ValidationError

from app.config import get_settings
from app.core.auth.exceptions import InvalidTokenError, TokenExpiredError
from app.core.auth.schemas import TokenPayload
from app.domains.users.models import UserRole


def create_access_token(user_id: int, username: str, role: UserRole) -> str:
    """Create a new JWT access token.

    Args:
        user_id: User's unique identifier.
        username: Username of the user.
        role: User's role for authorization.

    Returns:
        str: Encoded JWT access token.
    """
    jwt_settings = get_settings().JWT
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=jwt_settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "username": username,
        "role": role.value,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }

    return jwt.encode(
        payload,
        jwt_settings.SECRET_KEY.get_secret_value(),
        algorithm=jwt_settings.ALGORITHM,
    )


def create_refresh_token(user_id: int) -> str:
    """Create a new JWT refresh token.

    Args:
        user_id: User's unique identifier.

    Returns:
        str: Encoded JWT refresh token.
    """
    jwt_settings = get_settings().JWT
    now = datetime.now(UTC)
    expires = now + timedelta(days=jwt_settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "exp": int(expires.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }

    return jwt.encode(
        payload,
        jwt_settings.SECRET_KEY.get_secret_value(),
        algorithm=jwt_settings.ALGORITHM,
    )


def verify_token(token: str, token_type: Literal["access", "refresh"]) -> TokenPayload:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string to verify.
        token_type: Expected token type ("access" or "refresh").

    Returns:
        TokenPayload: Validated token payload.

    Raises:
        TokenExpiredError: If token has expired.
        InvalidTokenError: If token is invalid or malformed.
    """
    jwt_settings = get_settings().JWT

    try:
        payload = jwt.decode(
            token,
            jwt_settings.SECRET_KEY.get_secret_value(),
            algorithms=[jwt_settings.ALGORITHM],
        )

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
