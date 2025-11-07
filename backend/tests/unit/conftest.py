from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.main import app


@pytest.fixture
def mock_session() -> AsyncMock:
    """Return a mocked AsyncSession for testing database operations."""
    mock = AsyncMock(spec=AsyncSession)
    mock.exec.return_value = MagicMock()
    return mock


@pytest.fixture(scope="session")
def api_prefix() -> str:
    """Return the API prefix."""
    return get_settings().API_PATH


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Return a test client with no authentication."""
    return TestClient(app)
