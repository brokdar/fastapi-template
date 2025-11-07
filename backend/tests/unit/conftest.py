import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture(scope="session")
def api_prefix() -> str:
    """Return the API prefix."""
    return get_settings().API_PATH


@pytest.fixture
def unauthenticated_client() -> TestClient:
    """Return a test client with no authentication."""
    return TestClient(app)
