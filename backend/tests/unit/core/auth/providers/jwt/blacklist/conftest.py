"""Shared fixtures for JWT blacklist tests."""

from unittest.mock import AsyncMock

import pytest

from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore
from app.core.auth.providers.jwt.blacklist.redis import RedisTokenBlacklistStore


@pytest.fixture
def memory_store() -> InMemoryTokenBlacklistStore:
    """Provide InMemoryTokenBlacklistStore instance for testing."""
    return InMemoryTokenBlacklistStore()


@pytest.fixture
def memory_store_low_threshold() -> InMemoryTokenBlacklistStore:
    """Provide InMemoryTokenBlacklistStore with low cleanup threshold."""
    return InMemoryTokenBlacklistStore(cleanup_threshold=3)


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Provide mocked async Redis client."""
    mock = AsyncMock()
    mock.setex = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def redis_store(mock_redis_client: AsyncMock) -> RedisTokenBlacklistStore:
    """Provide RedisTokenBlacklistStore with mocked Redis client."""
    return RedisTokenBlacklistStore(mock_redis_client)
