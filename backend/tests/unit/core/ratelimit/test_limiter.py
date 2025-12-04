"""Test suite for rate limit key functions."""

from unittest.mock import Mock

from fastapi import Request

from app.core.ratelimit import get_user_identifier, limiter


class TestGetUserIdentifier:
    """Test suite for the get_user_identifier key function."""

    def test_returns_user_id_when_user_present(self) -> None:
        """Test returns user-prefixed identifier when user is in request state."""
        request = Mock(spec=Request)
        user = Mock()
        user.id = 123
        request.state.user = user
        request.client = Mock()
        request.client.host = "192.168.1.1"

        result = get_user_identifier(request)

        assert result == "user:123"

    def test_returns_ip_when_no_user(self) -> None:
        """Test falls back to IP address when no user in request state."""
        request = Mock(spec=Request)
        request.state = Mock(spec=[])  # state with no 'user' attribute
        request.client = Mock()
        request.client.host = "10.0.0.5"

        result = get_user_identifier(request)

        assert result == "10.0.0.5"

    def test_returns_ip_when_user_is_none(self) -> None:
        """Test falls back to IP when user attribute exists but is None."""
        request = Mock(spec=Request)
        request.state.user = None
        request.client = Mock()
        request.client.host = "172.16.0.1"

        result = get_user_identifier(request)

        assert result == "172.16.0.1"

    def test_handles_user_with_string_id(self) -> None:
        """Test handles users with string IDs (e.g., UUIDs)."""
        request = Mock(spec=Request)
        user = Mock()
        user.id = "abc-123-def"
        request.state.user = user
        request.client = Mock()
        request.client.host = "192.168.1.1"

        result = get_user_identifier(request)

        assert result == "user:abc-123-def"


class TestLimiterInstance:
    """Test suite for the shared limiter instance."""

    def test_limiter_is_configured(self) -> None:
        """Test that limiter instance exists and is configured."""
        assert limiter is not None

    def test_limiter_has_limit_decorator(self) -> None:
        """Test that limiter exposes the limit decorator method."""
        assert hasattr(limiter, "limit")
        assert callable(limiter.limit)
