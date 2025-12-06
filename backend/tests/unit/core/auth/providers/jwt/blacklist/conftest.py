"""Shared fixtures for JWT blacklist tests."""

import pytest

from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore


@pytest.fixture
def memory_store() -> InMemoryTokenBlacklistStore:
    """Provide InMemoryTokenBlacklistStore instance for testing."""
    return InMemoryTokenBlacklistStore()


@pytest.fixture
def memory_store_low_threshold() -> InMemoryTokenBlacklistStore:
    """Provide InMemoryTokenBlacklistStore with low cleanup threshold."""
    return InMemoryTokenBlacklistStore(cleanup_threshold=3)
