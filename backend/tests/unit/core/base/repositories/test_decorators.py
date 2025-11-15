"""Test suite for repository decorators."""

from typing import Any

import pytest

from app.core.pagination.exceptions import InvalidPaginationError
from app.core.pagination.validation import validate_pagination


class TestValidatePaginationDecorator:
    """Test suite for validate_pagination decorator."""

    @pytest.mark.asyncio
    async def test_executes_function_with_valid_pagination_parameters(self) -> None:
        """Test successful execution with valid pagination parameters."""

        @validate_pagination
        async def mock_function(limit: int, offset: int = 0) -> str:
            return f"limit={limit}, offset={offset}"

        result = await mock_function(limit=10, offset=5)
        assert result == "limit=10, offset=5"

    @pytest.mark.asyncio
    async def test_executes_function_without_pagination_parameters(self) -> None:
        """Test successful execution without pagination parameters."""

        @validate_pagination
        async def mock_function(name: str) -> str:
            return f"name={name}"

        result = await mock_function(name="test")
        assert result == "name=test"

    @pytest.mark.asyncio
    async def test_executes_function_with_only_limit_parameter(self) -> None:
        """Test successful execution with only limit parameter."""

        @validate_pagination
        async def mock_function(limit: int) -> str:
            return f"limit={limit}"

        result = await mock_function(limit=25)
        assert result == "limit=25"

    @pytest.mark.asyncio
    async def test_executes_function_with_only_offset_parameter(self) -> None:
        """Test successful execution with only offset parameter."""

        @validate_pagination
        async def mock_function(offset: int) -> str:
            return f"offset={offset}"

        result = await mock_function(offset=10)
        assert result == "offset=10"

    @pytest.mark.parametrize(
        ("limit", "expected_error"),
        [
            (0, "must be positive integer"),
            (-1, "must be positive integer"),
            (-100, "must be positive integer"),
        ],
        ids=["zero_limit", "negative_one", "large_negative"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_limit(
        self, limit: int, expected_error: str
    ) -> None:
        """Test InvalidPaginationError for invalid limit values."""

        @validate_pagination
        async def mock_function(limit: int) -> str:
            return f"limit={limit}"

        with pytest.raises(
            InvalidPaginationError,
            match=rf"Invalid pagination parameter 'limit'.*value={limit}.*{expected_error}",
        ):
            await mock_function(limit=limit)

    @pytest.mark.parametrize(
        "limit_value",
        ["10", None, 3.14, [], {}],
        ids=["string", "none", "float", "list", "dict"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_non_integer_limit(
        self, limit_value: Any
    ) -> None:
        """Test InvalidPaginationError for non-integer limit values."""

        @validate_pagination
        async def mock_function(limit: Any) -> str:
            return f"limit={limit}"

        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'limit'.*must be positive integer",
        ):
            await mock_function(limit=limit_value)

    @pytest.mark.parametrize(
        ("offset", "expected_error"),
        [
            (-1, "must be non-negative integer"),
            (-5, "must be non-negative integer"),
            (-100, "must be non-negative integer"),
        ],
        ids=["negative_one", "negative_small", "negative_large"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_offset(
        self, offset: int, expected_error: str
    ) -> None:
        """Test InvalidPaginationError for invalid offset values."""

        @validate_pagination
        async def mock_function(offset: int) -> str:
            return f"offset={offset}"

        with pytest.raises(
            InvalidPaginationError,
            match=rf"Invalid pagination parameter 'offset'.*value={offset}.*{expected_error}",
        ):
            await mock_function(offset=offset)

    @pytest.mark.parametrize(
        "offset_value",
        ["-5", None, 2.5, [], {}],
        ids=["string", "none", "float", "list", "dict"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_non_integer_offset(
        self, offset_value: Any
    ) -> None:
        """Test InvalidPaginationError for non-integer offset values."""

        @validate_pagination
        async def mock_function(offset: Any) -> str:
            return f"offset={offset}"

        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await mock_function(offset=offset_value)

    @pytest.mark.asyncio
    async def test_validates_both_limit_and_offset_parameters(self) -> None:
        """Test validation of both limit and offset parameters."""

        @validate_pagination
        async def mock_function(limit: int, offset: int) -> str:
            return f"limit={limit}, offset={offset}"

        result = await mock_function(limit=20, offset=10)
        assert result == "limit=20, offset=10"

    @pytest.mark.asyncio
    async def test_raises_error_for_invalid_limit_with_valid_offset(self) -> None:
        """Test error for invalid limit with valid offset."""

        @validate_pagination
        async def mock_function(limit: int, offset: int) -> str:
            return f"limit={limit}, offset={offset}"

        with pytest.raises(
            InvalidPaginationError, match=r"Invalid pagination parameter 'limit'"
        ):
            await mock_function(limit=0, offset=10)

    @pytest.mark.asyncio
    async def test_raises_error_for_valid_limit_with_invalid_offset(self) -> None:
        """Test error for valid limit with invalid offset."""

        @validate_pagination
        async def mock_function(limit: int, offset: int) -> str:
            return f"limit={limit}, offset={offset}"

        with pytest.raises(
            InvalidPaginationError, match=r"Invalid pagination parameter 'offset'"
        ):
            await mock_function(limit=10, offset=-1)

    @pytest.mark.asyncio
    async def test_allows_zero_offset(self) -> None:
        """Test that zero offset is valid."""

        @validate_pagination
        async def mock_function(limit: int, offset: int) -> str:
            return f"limit={limit}, offset={offset}"

        result = await mock_function(limit=10, offset=0)
        assert result == "limit=10, offset=0"

    @pytest.mark.asyncio
    async def test_passes_positional_arguments_correctly(self) -> None:
        """Test that positional arguments are passed correctly."""

        @validate_pagination
        async def mock_function(name: str, limit: int, offset: int = 0) -> str:
            return f"name={name}, limit={limit}, offset={offset}"

        result = await mock_function("test", limit=10, offset=5)
        assert result == "name=test, limit=10, offset=5"

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        """Test that decorated function preserves original metadata."""

        @validate_pagination
        async def test_function(limit: int) -> str:
            """Test function docstring."""
            return f"limit={limit}"

        assert test_function.__name__ == "test_function"
        assert "Test function docstring." in str(test_function.__doc__)

    @pytest.mark.asyncio
    async def test_handles_complex_function_signatures(self) -> None:
        """Test decorator with complex function signatures."""

        @validate_pagination
        async def complex_function(
            required_arg: str, *args: str, limit: int, offset: int = 0, **kwargs: Any
        ) -> str:
            return f"args={len(args)}, kwargs={len(kwargs)}, limit={limit}"

        result = await complex_function(
            "required", "extra1", "extra2", limit=15, offset=5, custom_param="value"
        )
        assert "args=2" in result
        assert "kwargs=1" in result
        assert "limit=15" in result
