"""Test suite for health check endpoint."""

from datetime import UTC, datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from pytest_mock import MockerFixture

from app.domains.health.schemas import HealthResponse


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    def test_returns_200_ok_status_code(
        self, unauthenticated_client: TestClient, api_prefix: str
    ) -> None:
        """Test health check returns 200 OK status."""
        response = unauthenticated_client.get(f"{api_prefix}/health")
        assert response.status_code == status.HTTP_200_OK

    def test_returns_valid_response_structure(
        self, unauthenticated_client: TestClient, api_prefix: str
    ) -> None:
        """Test health check response contains expected structure."""
        response = unauthenticated_client.get(f"{api_prefix}/health")

        adapter = TypeAdapter(HealthResponse)
        health_response = adapter.validate_python(response.json())
        assert health_response.status == "healthy"
        assert health_response.timestamp is not None
        assert health_response.timestamp.tzinfo is not None

    @pytest.mark.parametrize(
        "test_time",
        [
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            datetime(2024, 6, 15, 18, 30, 0, tzinfo=UTC),
            datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
        ],
        ids=["start_of_year", "mid_year", "end_of_year"],
    )
    def test_returns_mocked_timestamp_correctly(
        self,
        unauthenticated_client: TestClient,
        api_prefix: str,
        test_time: datetime,
        mocker: MockerFixture,
    ) -> None:
        """Test health check uses system datetime for timestamp."""
        mock_datetime = mocker.patch("app.domains.health.schemas.datetime")
        mock_datetime.now.return_value = test_time
        mock_datetime.UTC = UTC

        response = unauthenticated_client.get(f"{api_prefix}/health")

        adapter = TypeAdapter(HealthResponse)
        health_response = adapter.validate_python(response.json())

        assert health_response.timestamp == test_time
        assert health_response.status == "healthy"
