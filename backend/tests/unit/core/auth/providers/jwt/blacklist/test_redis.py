"""Unit tests for RedisTokenBlacklistStore."""

from unittest.mock import AsyncMock

import pytest

from app.core.auth.providers.jwt.blacklist.redis import RedisTokenBlacklistStore


class TestRedisTokenBlacklistStoreAdd:
    """Test suite for RedisTokenBlacklistStore.add method."""

    @pytest.mark.asyncio
    async def test_calls_setex_with_correct_parameters(
        self,
        redis_store: RedisTokenBlacklistStore,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test that add calls Redis SETEX with correct parameters."""
        await redis_store.add("test-jti-123", expires_in_seconds=300)

        mock_redis_client.setex.assert_called_once_with(
            "jwt:blacklist:test-jti-123",
            300,
            "1",
        )

    @pytest.mark.asyncio
    async def test_uses_correct_key_prefix(
        self,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test that custom key prefix is applied correctly."""
        store = RedisTokenBlacklistStore(
            mock_redis_client,
            key_prefix="custom:prefix:",
        )

        await store.add("test-jti", expires_in_seconds=100)

        mock_redis_client.setex.assert_called_once_with(
            "custom:prefix:test-jti",
            100,
            "1",
        )


class TestRedisTokenBlacklistStoreIsBlacklisted:
    """Test suite for RedisTokenBlacklistStore.is_blacklisted method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_key_exists(
        self,
        redis_store: RedisTokenBlacklistStore,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test that is_blacklisted returns True when key exists."""
        mock_redis_client.exists = AsyncMock(return_value=1)

        result = await redis_store.is_blacklisted("test-jti")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("jwt:blacklist:test-jti")

    @pytest.mark.asyncio
    async def test_returns_false_when_key_missing(
        self,
        redis_store: RedisTokenBlacklistStore,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test that is_blacklisted returns False when key doesn't exist."""
        mock_redis_client.exists = AsyncMock(return_value=0)

        result = await redis_store.is_blacklisted("test-jti")

        assert result is False

    @pytest.mark.asyncio
    async def test_uses_correct_key_prefix(
        self,
        mock_redis_client: AsyncMock,
    ) -> None:
        """Test that custom key prefix is used for existence check."""
        store = RedisTokenBlacklistStore(
            mock_redis_client,
            key_prefix="auth:revoked:",
        )
        mock_redis_client.exists = AsyncMock(return_value=1)

        await store.is_blacklisted("my-jti")

        mock_redis_client.exists.assert_called_once_with("auth:revoked:my-jti")
