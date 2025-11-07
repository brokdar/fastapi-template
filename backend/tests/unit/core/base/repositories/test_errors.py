"""Test suite for repository error classes."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import exc as sqlalchemy_exc

from app.core.base.repositories.exceptions import (
    EntityNotFoundError,
    RepositoryConnectionError,
    RepositoryError,
    RepositoryIntegrityError,
    RepositoryOperationError,
    handle_repository_errors,
)
from app.core.exceptions.base import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)
from app.core.pagination.exceptions import InvalidPaginationError


class TestRepositoryError:
    """Test suite for RepositoryError."""

    def test_inherits_from_database_error(self) -> None:
        """Test RepositoryError inheritance."""
        error = RepositoryError()
        assert isinstance(error, DatabaseError)

    def test_creates_error_with_default_message(self) -> None:
        """Test default error message."""
        error = RepositoryError()
        assert "Repository operation failed" in str(error)

    def test_creates_error_with_custom_message(self) -> None:
        """Test custom error message."""
        error = RepositoryError("Custom error message")
        assert "Custom error message" in str(error)

    def test_creates_error_with_details(self) -> None:
        """Test error with details dictionary."""
        details = {"operation": "create", "entity": "User"}
        error = RepositoryError("Test error", details=details)
        assert error.details == details

    def test_creates_error_with_headers(self) -> None:
        """Test error with headers dictionary."""
        headers = {"X-Custom": "value"}
        error = RepositoryError("Test error", headers=headers)
        assert error.headers == headers


class TestEntityNotFoundError:
    """Test suite for EntityNotFoundError."""

    def test_inherits_from_not_found_error(self) -> None:
        """Test EntityNotFoundError inheritance."""
        error = EntityNotFoundError("User", 123)
        assert isinstance(error, NotFoundError)

    def test_creates_error_with_entity_context(self) -> None:
        """Test error with entity type and ID."""
        error = EntityNotFoundError("User", 123)
        assert "User with ID 123 not found" in str(error)

    def test_includes_entity_details_in_context(self) -> None:
        """Test entity details in error context."""
        error = EntityNotFoundError("User", 123)
        assert error.details["entity_type"] == "User"
        assert error.details["entity_id"] == 123

    def test_merges_additional_details(self) -> None:
        """Test merging of additional details."""
        additional_details = {"query": "SELECT * FROM users"}
        error = EntityNotFoundError("User", 123, details=additional_details)
        assert error.details["entity_type"] == "User"
        assert error.details["entity_id"] == 123
        assert error.details["query"] == "SELECT * FROM users"

    @pytest.mark.parametrize(
        ("entity_type", "entity_id"),
        [
            ("User", 1),
            ("Document", "abc-123"),
            ("Order", 99999),
            ("Product", None),
        ],
        ids=["int_id", "string_id", "large_id", "none_id"],
    )
    def test_handles_various_entity_types_and_ids(
        self, entity_type: str, entity_id: Any
    ) -> None:
        """Test various entity types and ID formats."""
        error = EntityNotFoundError(entity_type, entity_id)
        assert entity_type in str(error)
        assert str(entity_id) in str(error)


class TestInvalidPaginationError:
    """Test suite for InvalidPaginationError."""

    def test_inherits_from_validation_error(self) -> None:
        """Test InvalidPaginationError inheritance."""
        error = InvalidPaginationError("limit", 0, "must be positive")
        assert isinstance(error, ValidationError)

    def test_creates_error_with_parameter_context(self) -> None:
        """Test error with parameter validation context."""
        error = InvalidPaginationError("limit", 0, "must be positive")
        # assert "Invalid pagination parameter 'limit'" in str(error)
        assert "value=0" in str(error)
        assert "must be positive" in str(error)

    def test_includes_parameter_details_in_context(self) -> None:
        """Test parameter details in error context."""
        error = InvalidPaginationError("limit", -5, "must be positive integer")
        assert error.details["parameter"] == "limit"
        assert error.details["value"] == -5
        assert error.details["constraint"] == "must be positive integer"

    @pytest.mark.parametrize(
        ("parameter", "value", "constraint"),
        [
            ("limit", 0, "must be positive integer"),
            ("offset", -1, "must be non-negative integer"),
            ("limit", "10", "must be positive integer"),
            ("offset", None, "must be non-negative integer"),
        ],
        ids=["zero_limit", "negative_offset", "string_limit", "none_offset"],
    )
    def test_handles_various_invalid_parameters(
        self, parameter: str, value: Any, constraint: str
    ) -> None:
        """Test various invalid parameter scenarios."""
        error = InvalidPaginationError(parameter, value, constraint)
        assert parameter in str(error)
        assert str(value) in str(error)
        assert constraint in str(error)


class TestRepositoryOperationError:
    """Test suite for RepositoryOperationError."""

    def test_inherits_from_repository_error(self) -> None:
        """Test RepositoryOperationError inheritance."""
        original_error = Exception("Database error")
        error = RepositoryOperationError("create", "User", original_error)
        assert isinstance(error, RepositoryError)

    def test_creates_error_with_operation_context(self) -> None:
        """Test error with operation context."""
        original_error = Exception("Connection failed")
        error = RepositoryOperationError("create", "User", original_error)
        assert "Database operation 'create' failed for User" in str(error)
        assert "Connection failed" in str(error)

    def test_includes_operation_details_in_context(self) -> None:
        """Test operation details in error context."""
        original_error = ValueError("Invalid data")
        error = RepositoryOperationError("update", "Product", original_error)
        assert error.details["operation"] == "update"
        assert error.details["entity_type"] == "Product"
        assert error.details["original_error"] == "Invalid data"
        assert error.details["original_error_type"] == "ValueError"


class TestRepositoryIntegrityError:
    """Test suite for RepositoryIntegrityError."""

    def test_inherits_from_conflict_error(self) -> None:
        """Test RepositoryIntegrityError inheritance."""
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())
        error = RepositoryIntegrityError("unique", "User", original_error)
        assert isinstance(error, ConflictError)

    def test_creates_error_with_constraint_context(self) -> None:
        """Test error with constraint violation context."""
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())
        error = RepositoryIntegrityError("unique", "User", original_error)
        assert "Integrity constraint violation for User" in str(error)
        assert "unique constraint failed" in str(error)

    def test_includes_constraint_details_in_context(self) -> None:
        """Test constraint details in error context."""
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())
        original_error.statement = "INSERT INTO users ..."
        original_error.params = {"name": "John"}
        error = RepositoryIntegrityError("foreign key", "Order", original_error)

        assert error.details["constraint_type"] == "foreign key"
        assert error.details["entity_type"] == "Order"
        assert error.details["statement"] == "INSERT INTO users ..."
        assert error.details["params"] == {"name": "John"}

    @pytest.mark.parametrize(
        "constraint_type",
        ["unique", "foreign key", "check", "not null"],
        ids=["unique_constraint", "fk_constraint", "check_constraint", "not_null"],
    )
    def test_handles_various_constraint_types(self, constraint_type: str) -> None:
        """Test various constraint violation types."""
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())
        error = RepositoryIntegrityError(constraint_type, "User", original_error)
        assert constraint_type in str(error)


class TestRepositoryConnectionError:
    """Test suite for RepositoryConnectionError."""

    def test_inherits_from_repository_error(self) -> None:
        """Test RepositoryConnectionError inheritance."""
        original_error = ConnectionError("Network unreachable")
        error = RepositoryConnectionError("connect", original_error)
        assert isinstance(error, RepositoryError)

    def test_creates_error_with_connection_context(self) -> None:
        """Test error with connection failure context."""
        original_error = TimeoutError("Connection timeout")
        error = RepositoryConnectionError("query", original_error)
        assert "Database connection failed during 'query'" in str(error)
        assert "Connection timeout" in str(error)

    def test_includes_connection_details_in_context(self) -> None:
        """Test connection details in error context."""
        original_error = OSError("Network unreachable")
        error = RepositoryConnectionError("transaction", original_error)
        assert error.details["operation"] == "transaction"
        assert error.details["original_error"] == "Network unreachable"
        assert error.details["original_error_type"] == "OSError"


class TestHandleRepositoryErrorsDecorator:
    """Test suite for handle_repository_errors decorator."""

    @pytest.mark.asyncio
    async def test_executes_function_successfully_when_no_errors(self) -> None:
        """Test successful function execution without errors."""

        @handle_repository_errors()
        async def successful_function(value: int) -> int:
            return value * 2

        result = await successful_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_transforms_integrity_error_to_repository_integrity_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test SQLAlchemy IntegrityError transformation."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())

        @handle_repository_errors("TestEntity")
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await failing_function()

        assert exc_info.value.details["entity_type"] == "TestEntity"
        assert exc_info.value.details["constraint_type"] == "integrity"

    @pytest.mark.parametrize(
        ("error_message", "expected_constraint_type"),
        [
            ("UNIQUE constraint failed", "unique"),
            ("duplicate key value", "unique"),
            ("foreign key constraint fails", "foreign key"),
            ("violates fk_users_role_id", "foreign key"),
            ("check constraint failed", "check"),
            ("some other integrity error", "integrity"),
        ],
        ids=[
            "unique_keyword",
            "duplicate_keyword",
            "fk_keyword",
            "fk_prefix",
            "check_keyword",
            "generic",
        ],
    )
    @pytest.mark.asyncio
    async def test_detects_constraint_type_from_error_message(
        self, error_message: str, expected_constraint_type: str, mocker: MockerFixture
    ) -> None:
        """Test constraint type detection from error messages."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.IntegrityError(error_message, "", MagicMock())

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await failing_function()

        assert exc_info.value.details["constraint_type"] == expected_constraint_type

    @pytest.mark.asyncio
    async def test_transforms_connection_operational_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test OperationalError with connection keywords transformation."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.OperationalError(
            "connection timeout", "", MagicMock()
        )

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryConnectionError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_transforms_non_connection_operational_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test OperationalError without connection keywords transformation."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.OperationalError("disk full", "", MagicMock())

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryOperationError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_transforms_database_error_to_operation_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test DatabaseError transformation."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.DatabaseError("", "", MagicMock())

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryOperationError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_transforms_statement_error_to_operation_error(
        self, mocker: MockerFixture
    ) -> None:
        """Test StatementError transformation."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.StatementError("", "", "", MagicMock())
        original_error.statement = "SELECT * FROM invalid"
        original_error.params = {"id": 1}

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryOperationError):
            await failing_function()

    @pytest.mark.asyncio
    async def test_auto_detects_entity_type_from_repository_instance(
        self, mocker: MockerFixture
    ) -> None:
        """Test entity type auto-detection from repository instance."""
        mocker.patch("app.core.base.repositories.exceptions.logger")

        class MockRepository:
            class MockModel:
                pass

            model_class = MockModel

        mock_repo = MockRepository()
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())

        @handle_repository_errors()
        async def repository_method(self: MockRepository) -> None:
            raise original_error

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await repository_method(mock_repo)

        assert exc_info.value.details["entity_type"] == "MockModel"

    @pytest.mark.asyncio
    async def test_uses_unknown_entity_type_when_detection_fails(
        self, mocker: MockerFixture
    ) -> None:
        """Test fallback to Unknown entity type."""
        mocker.patch("app.core.base.repositories.exceptions.logger")
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())

        @handle_repository_errors()
        async def standalone_function() -> None:
            raise original_error

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await standalone_function()

        assert exc_info.value.details["entity_type"] == "Unknown"

    @pytest.mark.asyncio
    async def test_preserves_original_exception_with_from_clause(self) -> None:
        """Test original exception is preserved with from clause."""
        original_error = sqlalchemy_exc.IntegrityError("", "", MagicMock())

        @handle_repository_errors()
        async def failing_function() -> None:
            raise original_error

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await failing_function()

        assert exc_info.value.__cause__ is original_error

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        """Test decorated function preserves original metadata."""

        @handle_repository_errors()
        async def test_function() -> str:
            """Test function docstring."""
            return "test"

        assert test_function.__name__ == "test_function"
        assert "Test function docstring." in str(test_function.__doc__)
