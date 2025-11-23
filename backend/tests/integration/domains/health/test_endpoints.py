"""Integration tests for health check endpoint."""

import httpx
import pytest
from pydantic import TypeAdapter

from app.domains.health.schemas import HealthResponse


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    @pytest.mark.asyncio
    async def test_returns_healthy_status(
        self,
        unauthorized_client: httpx.AsyncClient,
    ) -> None:
        """Test health endpoint returns 200 with valid response."""
        response = await unauthorized_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        validated_data = TypeAdapter(HealthResponse).validate_python(data)

        assert validated_data.status == "healthy"
        assert validated_data.timestamp is not None
