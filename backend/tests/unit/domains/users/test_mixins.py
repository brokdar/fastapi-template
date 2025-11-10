"""Test suite for ID parsing mixins."""

from uuid import UUID

import pytest

from app.domains.users.exceptions import InvalidUserIDError
from app.domains.users.mixins import IntIDMixin, UUIDIDMixin


class TestIntIDMixin:
    """Test integer ID parsing mixin."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("123", 123),
            ("0", 0),
            (456, 456),
            ("-1", -1),
            ("999999", 999999),
        ],
        ids=[
            "positive_string",
            "zero_string",
            "already_int",
            "negative",
            "large_number",
        ],
    )
    def test_parses_valid_integers(self, value: str | int, expected: int) -> None:
        """Test successful integer ID parsing for various valid inputs."""
        mixin = IntIDMixin()
        assert mixin.parse_id(value) == expected

    def test_raises_error_for_float(self) -> None:
        """Test that float values are explicitly rejected."""
        mixin = IntIDMixin()
        with pytest.raises(InvalidUserIDError, match="Float values not allowed"):
            mixin.parse_id(3.14)

    @pytest.mark.parametrize(
        "invalid_value",
        ["not_a_number", "12.5", "", "abc123", "123abc", " "],
        ids=[
            "text",
            "decimal_string",
            "empty_string",
            "alphanumeric_prefix",
            "alphanumeric_suffix",
            "whitespace",
        ],
    )
    def test_raises_error_for_invalid_formats(self, invalid_value: str) -> None:
        """Test that invalid integer formats raise InvalidUserIDError."""
        mixin = IntIDMixin()
        with pytest.raises(InvalidUserIDError, match="Cannot parse value as integer"):
            mixin.parse_id(invalid_value)

    def test_error_includes_value_and_type_details(self) -> None:
        """Test that InvalidUserIDError includes helpful context."""
        mixin = IntIDMixin()
        with pytest.raises(InvalidUserIDError) as exc_info:
            mixin.parse_id("invalid")

        assert exc_info.value.details is not None
        assert exc_info.value.details.get("value") == "invalid"
        assert exc_info.value.details.get("expected_type") == "int"


class TestUUIDIDMixin:
    """Test UUID ID parsing mixin."""

    def test_parses_valid_uuid_string(self) -> None:
        """Test successful UUID parsing from valid string."""
        mixin = UUIDIDMixin()
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"
        result = mixin.parse_id(uuid_str)

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_returns_uuid_instance_unchanged(self) -> None:
        """Test that UUID instances are returned as-is (passthrough)."""
        mixin = UUIDIDMixin()
        uuid_obj = UUID("123e4567-e89b-12d3-a456-426614174000")

        result = mixin.parse_id(uuid_obj)

        assert result is uuid_obj

    @pytest.mark.parametrize(
        "uuid_format",
        [
            "123e4567-e89b-12d3-a456-426614174000",
            "123E4567-E89B-12D3-A456-426614174000",
            "{123e4567-e89b-12d3-a456-426614174000}",
            "123e4567e89b12d3a456426614174000",
        ],
        ids=["lowercase_hyphens", "uppercase_hyphens", "braces", "no_hyphens"],
    )
    def test_parses_various_uuid_formats(self, uuid_format: str) -> None:
        """Test parsing of different valid UUID string formats."""
        mixin = UUIDIDMixin()
        result = mixin.parse_id(uuid_format)

        assert isinstance(result, UUID)

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "not-a-uuid",
            "12345",
            "",
            "abc-def-ghi",
            "123e4567-e89b-12d3-a456",
            "123e4567-e89b-12d3-a456-426614174000-extra",
        ],
        ids=[
            "text",
            "short_number",
            "empty_string",
            "wrong_format",
            "incomplete_uuid",
            "too_long",
        ],
    )
    def test_raises_error_for_invalid_formats(self, invalid_value: str) -> None:
        """Test that invalid UUID formats raise InvalidUserIDError."""
        mixin = UUIDIDMixin()
        with pytest.raises(InvalidUserIDError, match="Cannot parse value as UUID"):
            mixin.parse_id(invalid_value)

    def test_error_includes_value_and_type_details(self) -> None:
        """Test that InvalidUserIDError includes helpful context."""
        mixin = UUIDIDMixin()
        with pytest.raises(InvalidUserIDError) as exc_info:
            mixin.parse_id("not-a-uuid")

        assert exc_info.value.details is not None
        assert exc_info.value.details.get("value") == "not-a-uuid"
        assert exc_info.value.details.get("expected_type") == "UUID"
