"""JWT integration test fixtures."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest

from app.core.auth.providers.jwt.schemas import TokenResponse
from app.dependencies import jwt_provider


@pytest.fixture
def jwt_settings() -> dict[str, Any]:
    """Provide JWT configuration settings from the running app's provider."""
    return {
        "secret_key": jwt_provider.secret_key,
        "algorithm": jwt_provider.algorithm,
        "access_token_expire_minutes": jwt_provider.access_token_expire_minutes,
        "refresh_token_expire_days": jwt_provider.refresh_token_expire_days,
    }


@pytest.fixture
def expired_access_token(jwt_settings: dict[str, Any]) -> str:
    """Provide an expired access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": "999",
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "type": "access",
    }
    return jwt.encode(
        payload,
        jwt_settings["secret_key"],
        algorithm=jwt_settings["algorithm"],
    )


@pytest.fixture
def expired_refresh_token(jwt_settings: dict[str, Any]) -> str:
    """Provide an expired refresh token."""
    now = datetime.now(UTC)
    payload = {
        "sub": "999",
        "exp": int((now - timedelta(days=8)).timestamp()),
        "iat": int((now - timedelta(days=15)).timestamp()),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        jwt_settings["secret_key"],
        algorithm=jwt_settings["algorithm"],
    )


@pytest.fixture
def malformed_token() -> str:
    """Provide a malformed JWT token."""
    return "not.a.valid.jwt.token"


@pytest.fixture
def access_token_with_wrong_type(jwt_settings: dict[str, Any]) -> str:
    """Provide an access token with type claim set to refresh."""
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        jwt_settings["secret_key"],
        algorithm=jwt_settings["algorithm"],
    )


@pytest.fixture
def refresh_token_with_wrong_type(jwt_settings: dict[str, Any]) -> str:
    """Provide a refresh token with type claim set to access."""
    now = datetime.now(UTC)
    payload = {
        "sub": "1",
        "exp": int((now + timedelta(days=7)).timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    }
    return jwt.encode(
        payload,
        jwt_settings["secret_key"],
        algorithm=jwt_settings["algorithm"],
    )


@pytest.fixture
async def login_tokens(
    unauthorized_client: httpx.AsyncClient,
    ensure_test_users: Any,
    normal_user_credentials: dict[str, str],
) -> TokenResponse:
    """Provide fresh login tokens for the normal user."""
    response = await unauthorized_client.post(
        "/auth/jwt/login",
        data=normal_user_credentials,
    )
    assert response.status_code == 200
    return TokenResponse(**response.json())
