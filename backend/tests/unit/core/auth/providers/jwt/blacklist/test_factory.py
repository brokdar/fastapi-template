"""Unit tests for blacklist store factory."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import RedisDsn

from app.core.auth.providers.jwt.blacklist.factory import (
    _mask_redis_url,
    create_blacklist_store,
)
from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore
from app.core.auth.providers.jwt.blacklist.redis import RedisTokenBlacklistStore


class TestCreateBlacklistStore:
    """Test suite for create_blacklist_store factory function."""

    def test_creates_memory_store_when_url_is_none(self) -> None:
        """Test that factory creates in-memory store when no URL provided."""
        store = create_blacklist_store(redis_url=None)

        assert isinstance(store, InMemoryTokenBlacklistStore)

    def test_creates_memory_store_when_url_not_provided(self) -> None:
        """Test that factory creates in-memory store with default argument."""
        store = create_blacklist_store()

        assert isinstance(store, InMemoryTokenBlacklistStore)

    def test_creates_redis_store_when_url_provided(self) -> None:
        """Test that factory creates Redis store when URL provided."""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_client = MagicMock()
            mock_redis_class.from_url.return_value = mock_redis_client
            redis_url = RedisDsn("redis://localhost:6379/0")

            store = create_blacklist_store(redis_url=redis_url)

            assert isinstance(store, RedisTokenBlacklistStore)
            mock_redis_class.from_url.assert_called_once_with(
                "redis://localhost:6379/0"
            )

    def test_passes_redis_client_to_store(self) -> None:
        """Test that factory passes Redis client to store correctly."""
        with patch("redis.asyncio.Redis") as mock_redis_class:
            mock_redis_client = MagicMock()
            mock_redis_class.from_url.return_value = mock_redis_client
            redis_url = RedisDsn("redis://localhost:6379/0")

            store = create_blacklist_store(redis_url=redis_url)

            assert isinstance(store, RedisTokenBlacklistStore)
            assert store._redis is mock_redis_client


class TestMaskRedisUrl:
    """Test suite for _mask_redis_url helper function."""

    def test_masks_password_in_url_with_credentials(self) -> None:
        """Test that password is masked in URL with credentials."""
        url = RedisDsn("redis://user:secretpassword@localhost:6379/0")

        masked = _mask_redis_url(url)

        assert masked == "redis://user:***@localhost:6379/0"

    def test_preserves_url_without_credentials(self) -> None:
        """Test that URL without credentials is unchanged."""
        url = RedisDsn("redis://localhost:6379/0")

        masked = _mask_redis_url(url)

        assert masked == "redis://localhost:6379/0"

    def test_preserves_url_with_username_only(self) -> None:
        """Test that URL with username but no password is unchanged."""
        url = RedisDsn("redis://user@localhost:6379/0")

        masked = _mask_redis_url(url)

        assert masked == "redis://user@localhost:6379/0"

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            # RedisDsn normalizes URLs by adding default path /0 when not provided
            (RedisDsn("redis://:password@host:6379"), "redis://:***@host:6379/0"),
            (RedisDsn("redis://user:pass@host:6379"), "redis://user:***@host:6379/0"),
            (RedisDsn("redis://host:6379/0"), "redis://host:6379/0"),
            (RedisDsn("redis://user@host:6379"), "redis://user@host:6379/0"),
            (RedisDsn("redis://user:pass@host:6379/0"), "redis://user:***@host:6379/0"),
            (RedisDsn("redis://user:pass@host:6379/1"), "redis://user:***@host:6379/1"),
        ],
    )
    def test_handles_various_url_formats(self, url: RedisDsn, expected: str) -> None:
        """Test that various URL formats are handled correctly."""
        assert _mask_redis_url(url) == expected
