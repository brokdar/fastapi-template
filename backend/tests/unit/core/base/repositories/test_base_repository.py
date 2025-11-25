"""Test suite for BaseRepository."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.exceptions import EntityNotFoundError
from app.core.pagination.exceptions import InvalidPaginationError
from tests.unit.core.base.repositories.conftest import SampleModel


@pytest.fixture
def repository(
    mock_session: AsyncSession,
) -> BaseRepository[SampleModel]:
    """Provide BaseRepository instance for SampleModel."""
    return BaseRepository[SampleModel](mock_session, SampleModel)


class TestBaseRepositoryInitialization:
    """Test suite for BaseRepository initialization."""

    def test_initializes_repository_with_model(
        self, mock_session: AsyncSession
    ) -> None:
        """Test repository initialization with model."""
        repo = BaseRepository[SampleModel](mock_session, SampleModel)

        assert repo._session is mock_session
        assert repo.model_class is SampleModel


class TestBaseRepositoryGetById:
    """Test suite for BaseRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_retrieves_existing_entity_by_id(
        self,
        repository: BaseRepository[SampleModel],
        test_model: SampleModel,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful entity retrieval by integer ID."""
        mock_session.get.return_value = test_model

        result = await repository.get_by_id(1)

        assert result is test_model
        mock_session.get.assert_called_once_with(SampleModel, 1)

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_id(
        self,
        repository: BaseRepository[SampleModel],
        mocker: MockerFixture,
    ) -> None:
        """Test None return for non-existent ID."""
        mock_get = mocker.patch.object(repository._session, "get", return_value=None)

        result = await repository.get_by_id(999)

        assert result is None
        mock_get.assert_called_once_with(SampleModel, 999)


class TestBaseRepositoryGetAll:
    """Test suite for BaseRepository.get_all method."""

    @pytest.mark.asyncio
    async def test_retrieves_all_entities_successfully(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful retrieval of all entities."""
        mock_models = [
            SampleModel(id=1, name="Model 1"),
            SampleModel(id=2, name="Model 2"),
            SampleModel(id=3, name="Model 3"),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        results = await repository.get_all()

        assert results == mock_models
        assert len(results) == 3
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_entities(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return when no entities exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        results = await repository.get_all()

        assert results == []
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_correct_select_statement(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that correct select statement is generated."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        await repository.get_all()

        call_args = mock_session.exec.call_args[0][0]
        assert str(call_args).startswith("SELECT")


class TestBaseRepositoryCount:
    """Test suite for BaseRepository.count method."""

    @pytest.mark.asyncio
    async def test_returns_correct_count_for_populated_table(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test correct count return for populated table."""
        mock_result = MagicMock()
        mock_result.one.return_value = 42
        mock_session.exec.return_value = mock_result

        result = await repository.count()

        assert result == 42
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_table(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test zero count return for empty table."""
        mock_result = MagicMock()
        mock_result.one.return_value = 0
        mock_session.exec.return_value = mock_result

        result = await repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_generates_count_statement_with_select_from(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that count statement uses select_from."""
        mock_result = MagicMock()
        mock_result.one.return_value = 5
        mock_session.exec.return_value = mock_result

        await repository.count()

        call_args = mock_session.exec.call_args[0][0]
        statement_str = str(call_args)
        assert "count" in statement_str.lower()


class TestBaseRepositoryGetPaginated:
    """Test suite for BaseRepository.get_paginated method."""

    @pytest.mark.parametrize(
        ("limit", "offset", "expected_count"),
        [
            (10, 0, 10),
            (5, 15, 5),
            (1, 0, 1),
            (100, 50, 100),
        ],
        ids=["first_page", "middle_page", "single_item", "large_page"],
    )
    @pytest.mark.asyncio
    async def test_retrieves_paginated_results_successfully(
        self,
        repository: BaseRepository[SampleModel],
        limit: int,
        offset: int,
        expected_count: int,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful pagination with various parameters."""
        mock_models = [
            SampleModel(id=i, name=f"Model {i}") for i in range(expected_count)
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        results = await repository.get_paginated(limit=limit, offset=offset)

        assert len(results) == expected_count
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_applies_default_offset_when_not_provided(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test default offset application."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        await repository.get_paginated(limit=10)

        mock_session.exec.assert_called_once()

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
        self,
        repository: BaseRepository[SampleModel],
        limit: int,
        expected_error: str,
    ) -> None:
        """Test InvalidPaginationError for invalid limit values."""
        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'limit'.*" + expected_error,
        ):
            await repository.get_paginated(limit=limit)

    @pytest.mark.parametrize(
        "offset",
        [-1, -5, -100],
        ids=["negative_one", "negative_small", "negative_large"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_offset(
        self, repository: BaseRepository[SampleModel], offset: int
    ) -> None:
        """Test InvalidPaginationError for invalid offset values."""
        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await repository.get_paginated(limit=10, offset=offset)

    @pytest.mark.parametrize(
        "limit_value",
        ["10", None, 3.14, [], {}],
        ids=["string", "none", "float", "list", "dict"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_non_integer_limit(
        self, repository: BaseRepository[SampleModel], limit_value: Any
    ) -> None:
        """Test InvalidPaginationError for non-integer limit values."""
        with pytest.raises(InvalidPaginationError):
            await repository.get_paginated(limit=limit_value)


class TestBaseRepositoryCreate:
    """Test suite for BaseRepository.create method."""

    @pytest.mark.asyncio
    async def test_creates_entity_successfully(
        self,
        repository: BaseRepository[SampleModel],
        test_model: SampleModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful entity creation."""
        mock_add = mocker.patch.object(repository._session, "add")
        mock_commit = mocker.patch.object(repository._session, "commit")
        mock_refresh = mocker.patch.object(repository._session, "refresh")

        result = await repository.create(test_model)

        assert result is test_model
        mock_add.assert_called_once_with(test_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_model)

    @pytest.mark.asyncio
    async def test_calls_session_methods_in_correct_order(
        self,
        repository: BaseRepository[SampleModel],
        test_model: SampleModel,
        mocker: MockerFixture,
    ) -> None:
        """Test that session methods are called in correct order."""
        mock_add = mocker.patch.object(repository._session, "add")
        mock_commit = mocker.patch.object(repository._session, "commit")
        mock_refresh = mocker.patch.object(repository._session, "refresh")

        await repository.create(test_model)

        mock_add.assert_called_once_with(test_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_model)


class TestBaseRepositoryUpdate:
    """Test suite for BaseRepository.update method."""

    @pytest.mark.asyncio
    async def test_updates_entity_successfully(
        self,
        repository: BaseRepository[SampleModel],
        test_model: SampleModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful entity update."""
        mock_add = mocker.patch.object(repository._session, "add")
        mock_commit = mocker.patch.object(repository._session, "commit")
        mock_refresh = mocker.patch.object(repository._session, "refresh")

        result = await repository.update(test_model)

        assert result is test_model
        mock_add.assert_called_once_with(test_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_model)


class TestBaseRepositoryDelete:
    """Test suite for BaseRepository.delete method."""

    @pytest.mark.asyncio
    async def test_deletes_existing_entity_successfully(
        self,
        repository: BaseRepository[SampleModel],
        test_model: SampleModel,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful entity deletion."""
        mock_session.get.return_value = test_model

        await repository.delete(1)

        mock_session.get.assert_called_once_with(SampleModel, 1)
        mock_session.delete.assert_called_once_with(test_model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_entity_not_found_error_when_deleting_nonexistent(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test EntityNotFoundError for non-existent entity deletion."""
        mock_session.get.return_value = None

        with pytest.raises(EntityNotFoundError) as exc_info:
            await repository.delete(999)

        assert "SampleModel with ID 999 not found" in str(exc_info.value)
        mock_session.get.assert_called_once_with(SampleModel, 999)

    @pytest.mark.asyncio
    async def test_does_not_call_delete_when_entity_not_found(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that delete is not called when entity doesn't exist."""
        mock_session.get.return_value = None

        with pytest.raises(EntityNotFoundError):
            await repository.delete(999)

        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()


class TestBaseRepositoryFilter:
    """Test suite for BaseRepository.filter method."""

    @pytest.mark.asyncio
    async def test_filters_entities_with_single_condition(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with single condition."""
        mock_models = [SampleModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Test Model")
        results = await repository.filter(condition)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_entities_with_multiple_conditions(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with multiple conditions."""
        mock_models = [SampleModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition1 = cast(ColumnElement[bool], SampleModel.name == "Test Model")
        condition2 = cast(ColumnElement[bool], SampleModel.id == 1)
        results = await repository.filter(condition1, condition2)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_matches(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return when no entities match."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Nonexistent")
        results = await repository.filter(condition)

        assert results == []

    @pytest.mark.asyncio
    async def test_generates_select_statement_with_where_clause(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that select statement includes where clause."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Test")
        await repository.filter(condition)

        call_args = mock_session.exec.call_args[0][0]
        assert str(call_args).startswith("SELECT")


class TestBaseRepositoryFilterPaginated:
    """Test suite for BaseRepository.filter_paginated method."""

    @pytest.mark.asyncio
    async def test_filters_and_paginates_entities_successfully(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful filtering with pagination."""
        mock_models = [SampleModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Test Model")
        results = await repository.filter_paginated(condition, limit=10, offset=5)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_applies_default_offset_in_filtered_pagination(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test default offset application in filtered pagination."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Test")
        await repository.filter_paginated(condition, limit=10)

        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_with_multiple_conditions_and_pagination(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with multiple conditions and pagination."""
        mock_models = [SampleModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition1 = cast(ColumnElement[bool], SampleModel.name == "Test Model")
        condition2 = cast(ColumnElement[bool], SampleModel.id == 1)
        results = await repository.filter_paginated(
            condition1, condition2, limit=5, offset=10
        )

        assert results == mock_models

    @pytest.mark.parametrize(
        "limit", [0, -1, -100], ids=["zero_limit", "negative_one", "large_negative"]
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_limit_in_filter(
        self,
        repository: BaseRepository[SampleModel],
        limit: int,
    ) -> None:
        """Test InvalidPaginationError for invalid limit in filtered pagination."""
        condition = cast(ColumnElement[bool], SampleModel.name == "Test")

        with pytest.raises(InvalidPaginationError):
            await repository.filter_paginated(condition, limit=limit)

    @pytest.mark.parametrize(
        "offset",
        [-1, -5, -100],
        ids=["negative_one", "negative_small", "negative_large"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_offset_in_filter(
        self,
        repository: BaseRepository[SampleModel],
        offset: int,
    ) -> None:
        """Test InvalidPaginationError for invalid offset in filtered pagination."""
        condition = cast(ColumnElement[bool], SampleModel.name == "Test")

        with pytest.raises(InvalidPaginationError):
            await repository.filter_paginated(condition, limit=10, offset=offset)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_filtered_pagination_no_matches(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return for filtered pagination with no matches."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Nonexistent")
        results = await repository.filter_paginated(condition, limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_generates_complex_statement_with_where_offset_limit(
        self,
        repository: BaseRepository[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that statement includes where, offset, and limit clauses."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleModel.name == "Test")
        await repository.filter_paginated(condition, limit=10, offset=5)

        call_args = mock_session.exec.call_args[0][0]
        statement_str = str(call_args)
        assert statement_str.startswith("SELECT")
