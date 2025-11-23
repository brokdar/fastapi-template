"""API key integration test fixtures."""

import httpx
import pytest

from app.core.auth.providers.api_key.schemas import APIKeyCreateResponse


@pytest.fixture
async def created_api_key(
    authenticated_client: httpx.AsyncClient,
) -> tuple[APIKeyCreateResponse, str]:
    """Create an API key for the normal user and return response with secret."""
    response = await authenticated_client.post(
        "/auth/api-keys",
        json={"name": "Test API Key"},
    )
    assert response.status_code == 201
    data = APIKeyCreateResponse(**response.json())
    return data, data.secret_key
