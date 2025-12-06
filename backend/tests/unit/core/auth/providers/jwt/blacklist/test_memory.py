"""Unit tests for InMemoryTokenBlacklistStore."""

import time
from unittest.mock import patch

import pytest

from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore


class TestInMemoryTokenBlacklistStoreAdd:
    """Test suite for InMemoryTokenBlacklistStore.add method."""

    @pytest.mark.asyncio
    async def test_adds_token_to_blacklist(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that add stores token JTI in the blacklist."""
        await memory_store.add("test-jti-123", expires_in_seconds=300)

        assert "test-jti-123" in memory_store._blacklist

    @pytest.mark.asyncio
    async def test_stores_correct_expiry_timestamp(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that add stores correct expiration timestamp."""
        before = time.time()
        await memory_store.add("test-jti", expires_in_seconds=600)
        after = time.time()

        expiry = memory_store._blacklist["test-jti"]
        assert before + 600 <= expiry <= after + 600

    @pytest.mark.asyncio
    async def test_overwrites_existing_entry(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that adding same JTI overwrites previous entry."""
        await memory_store.add("test-jti", expires_in_seconds=100)
        old_expiry = memory_store._blacklist["test-jti"]

        await memory_store.add("test-jti", expires_in_seconds=500)
        new_expiry = memory_store._blacklist["test-jti"]

        assert new_expiry > old_expiry

    @pytest.mark.asyncio
    async def test_triggers_cleanup_when_threshold_exceeded(
        self,
        memory_store_low_threshold: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that cleanup is triggered when threshold is exceeded."""
        with patch("time.time", return_value=1000.0):
            await memory_store_low_threshold.add("jti-1", expires_in_seconds=10)
            await memory_store_low_threshold.add("jti-2", expires_in_seconds=10)
            await memory_store_low_threshold.add("jti-3", expires_in_seconds=10)

        with patch("time.time", return_value=2000.0):
            await memory_store_low_threshold.add("jti-4", expires_in_seconds=100)

        assert len(memory_store_low_threshold._blacklist) == 1
        assert "jti-4" in memory_store_low_threshold._blacklist


class TestInMemoryTokenBlacklistStoreIsBlacklisted:
    """Test suite for InMemoryTokenBlacklistStore.is_blacklisted method."""

    @pytest.mark.asyncio
    async def test_returns_true_for_blacklisted_token(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that is_blacklisted returns True for added token."""
        await memory_store.add("test-jti", expires_in_seconds=300)

        result = await memory_store.is_blacklisted("test-jti")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_token(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that is_blacklisted returns False for unknown JTI."""
        result = await memory_store.is_blacklisted("unknown-jti")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_expired_entry(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that is_blacklisted returns False for expired entry."""
        with patch("time.time", return_value=1000.0):
            await memory_store.add("test-jti", expires_in_seconds=10)

        with patch("time.time", return_value=2000.0):
            result = await memory_store.is_blacklisted("test-jti")

        assert result is False

    @pytest.mark.asyncio
    async def test_removes_expired_entry_on_check(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that expired entry is removed when checked."""
        with patch("time.time", return_value=1000.0):
            await memory_store.add("test-jti", expires_in_seconds=10)

        assert "test-jti" in memory_store._blacklist

        with patch("time.time", return_value=2000.0):
            await memory_store.is_blacklisted("test-jti")

        assert "test-jti" not in memory_store._blacklist


class TestInMemoryTokenBlacklistStoreCleanup:
    """Test suite for InMemoryTokenBlacklistStore._cleanup_expired method."""

    @pytest.mark.asyncio
    async def test_removes_all_expired_entries(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that cleanup removes all expired entries."""
        with patch("time.time", return_value=1000.0):
            await memory_store.add("expired-1", expires_in_seconds=10)
            await memory_store.add("expired-2", expires_in_seconds=20)
            await memory_store.add("valid", expires_in_seconds=1000)

        with patch("time.time", return_value=1500.0):
            memory_store._cleanup_expired()

        assert "expired-1" not in memory_store._blacklist
        assert "expired-2" not in memory_store._blacklist
        assert "valid" in memory_store._blacklist

    @pytest.mark.asyncio
    async def test_handles_empty_blacklist(
        self,
        memory_store: InMemoryTokenBlacklistStore,
    ) -> None:
        """Test that cleanup handles empty blacklist gracefully."""
        memory_store._cleanup_expired()  # Should not raise

        assert len(memory_store._blacklist) == 0
