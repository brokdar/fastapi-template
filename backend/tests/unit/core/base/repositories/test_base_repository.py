"""Test suite for BaseRepository."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.exceptions import EntityNotFoundError
from app.core.pagination.exceptions import InvalidPaginationError
from tests.unit.core.base.repositories.conftest import SampleIntModel, SampleUUIDModel


@pytest.fixture
def int_repository(
    mock_session: AsyncSession,
) -> BaseRepository[SampleIntModel, int]:
    """Provide BaseRepository instance for SampleIntModel."""
    return BaseRepository[SampleIntModel, int](mock_session, SampleIntModel)


@pytest.fixture
def uuid_repository(
    mock_session: AsyncSession,
) -> BaseRepository[SampleUUIDModel, UUID]:
    """Provide BaseRepository instance for SampleUUIDModel."""
    return BaseRepository[SampleUUIDModel, UUID](mock_session, SampleUUIDModel)


class TestBaseRepositoryInitialization:
    """Test suite for BaseRepository initialization."""

    def test_initializes_repository_with_int_model(
        self, mock_session: AsyncSession
    ) -> None:
        """Test repository initialization with integer model."""
        repo = BaseRepository[SampleIntModel, int](mock_session, SampleIntModel)

        assert repo._session is mock_session
        assert repo.model_class is SampleIntModel

    def test_initializes_repository_with_uuid_model(
        self, mock_session: AsyncSession, sample_uuid: UUID
    ) -> None:
        """Test repository initialization with UUID model."""
        repo = BaseRepository[SampleUUIDModel, UUID](mock_session, SampleUUIDModel)

        assert repo._session is mock_session
        assert repo.model_class is SampleUUIDModel


class TestBaseRepositoryGetById:
    """Test suite for BaseRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_retrieves_existing_entity_by_int_id(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        test_int_model: SampleIntModel,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful entity retrieval by integer ID."""
        mock_session.get.return_value = test_int_model

        result = await int_repository.get_by_id(1)

        assert result is test_int_model
        mock_session.get.assert_called_once_with(SampleIntModel, 1)

    @pytest.mark.asyncio
    async def test_retrieves_existing_entity_by_uuid_id(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        test_uuid_model: SampleUUIDModel,
        sample_uuid: UUID,
        mocker: MockerFixture,
    ) -> None:
        """Test successful entity retrieval by UUID."""
        mock_get = mocker.patch.object(
            uuid_repository._session, "get", return_value=test_uuid_model
        )

        result = await uuid_repository.get_by_id(sample_uuid)

        assert result is test_uuid_model
        mock_get.assert_called_once_with(SampleUUIDModel, sample_uuid)

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_int_id(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mocker: MockerFixture,
    ) -> None:
        """Test None return for non-existent integer ID."""
        mock_get = mocker.patch.object(
            int_repository._session, "get", return_value=None
        )

        result = await int_repository.get_by_id(999)

        assert result is None
        mock_get.assert_called_once_with(SampleIntModel, 999)

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_uuid_id(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        sample_uuid: UUID,
        mocker: MockerFixture,
    ) -> None:
        """Test None return for non-existent UUID."""
        mock_get = mocker.patch.object(
            uuid_repository._session, "get", return_value=None
        )

        result = await uuid_repository.get_by_id(sample_uuid)

        assert result is None
        mock_get.assert_called_once_with(SampleUUIDModel, sample_uuid)


class TestBaseRepositoryGetAll:
    """Test suite for BaseRepository.get_all method."""

    @pytest.mark.asyncio
    async def test_retrieves_all_entities_successfully(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful retrieval of all entities."""
        mock_models = [
            SampleIntModel(id=1, name="Model 1"),
            SampleIntModel(id=2, name="Model 2"),
            SampleIntModel(id=3, name="Model 3"),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        results = await int_repository.get_all()

        assert results == mock_models
        assert len(results) == 3
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_entities(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return when no entities exist."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        results = await int_repository.get_all()

        assert results == []
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_correct_select_statement(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test that correct select statement is generated."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        await int_repository.get_all()

        call_args = mock_session.exec.call_args[0][0]
        assert str(call_args).startswith("SELECT")


class TestBaseRepositoryCount:
    """Test suite for BaseRepository.count method."""

    @pytest.mark.asyncio
    async def test_returns_correct_count_for_populated_table(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test correct count return for populated table."""
        mock_result = MagicMock()
        mock_result.one.return_value = 42
        mock_session.exec.return_value = mock_result

        result = await int_repository.count()

        assert result == 42
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_table(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test zero count return for empty table."""
        mock_result = MagicMock()
        mock_result.one.return_value = 0
        mock_session.exec.return_value = mock_result

        result = await int_repository.count()

        assert result == 0

    @pytest.mark.asyncio
    async def test_generates_count_statement_with_select_from(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test that count statement uses select_from."""
        mock_result = MagicMock()
        mock_result.one.return_value = 5
        mock_session.exec.return_value = mock_result

        await int_repository.count()

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
        int_repository: BaseRepository[SampleIntModel, int],
        limit: int,
        offset: int,
        expected_count: int,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful pagination with various parameters."""
        mock_models = [
            SampleIntModel(id=i, name=f"Model {i}") for i in range(expected_count)
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        results = await int_repository.get_paginated(limit=limit, offset=offset)

        assert len(results) == expected_count
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_applies_default_offset_when_not_provided(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test default offset application."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        await int_repository.get_paginated(limit=10)

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
        int_repository: BaseRepository[SampleIntModel, int],
        limit: int,
        expected_error: str,
    ) -> None:
        """Test InvalidPaginationError for invalid limit values."""
        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'limit'.*" + expected_error,
        ):
            await int_repository.get_paginated(limit=limit)

    @pytest.mark.parametrize(
        "offset",
        [-1, -5, -100],
        ids=["negative_one", "negative_small", "negative_large"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_offset(
        self, int_repository: BaseRepository[SampleIntModel, int], offset: int
    ) -> None:
        """Test InvalidPaginationError for invalid offset values."""
        with pytest.raises(
            InvalidPaginationError,
            match=r"Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await int_repository.get_paginated(limit=10, offset=offset)

    @pytest.mark.parametrize(
        "limit_value",
        ["10", None, 3.14, [], {}],
        ids=["string", "none", "float", "list", "dict"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_non_integer_limit(
        self, int_repository: BaseRepository[SampleIntModel, int], limit_value: Any
    ) -> None:
        """Test InvalidPaginationError for non-integer limit values."""
        with pytest.raises(InvalidPaginationError):
            await int_repository.get_paginated(limit=limit_value)


class TestBaseRepositoryCreate:
    """Test suite for BaseRepository.create method."""

    @pytest.mark.asyncio
    async def test_creates_entity_successfully(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        test_int_model: SampleIntModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful entity creation."""
        mock_add = mocker.patch.object(int_repository._session, "add")
        mock_commit = mocker.patch.object(int_repository._session, "commit")
        mock_refresh = mocker.patch.object(int_repository._session, "refresh")

        result = await int_repository.create(test_int_model)

        assert result is test_int_model
        mock_add.assert_called_once_with(test_int_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_int_model)

    @pytest.mark.asyncio
    async def test_creates_uuid_entity_successfully(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        test_uuid_model: SampleUUIDModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful UUID entity creation."""
        mock_add = mocker.patch.object(uuid_repository._session, "add")
        mock_commit = mocker.patch.object(uuid_repository._session, "commit")
        mock_refresh = mocker.patch.object(uuid_repository._session, "refresh")

        result = await uuid_repository.create(test_uuid_model)

        assert result is test_uuid_model
        mock_add.assert_called_once_with(test_uuid_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_uuid_model)

    @pytest.mark.asyncio
    async def test_calls_session_methods_in_correct_order(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        test_int_model: SampleIntModel,
        mocker: MockerFixture,
    ) -> None:
        """Test that session methods are called in correct order."""
        mock_add = mocker.patch.object(int_repository._session, "add")
        mock_commit = mocker.patch.object(int_repository._session, "commit")
        mock_refresh = mocker.patch.object(int_repository._session, "refresh")

        await int_repository.create(test_int_model)

        mock_add.assert_called_once_with(test_int_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_int_model)


class TestBaseRepositoryUpdate:
    """Test suite for BaseRepository.update method."""

    @pytest.mark.asyncio
    async def test_updates_entity_successfully(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        test_int_model: SampleIntModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful entity update."""
        mock_add = mocker.patch.object(int_repository._session, "add")
        mock_commit = mocker.patch.object(int_repository._session, "commit")
        mock_refresh = mocker.patch.object(int_repository._session, "refresh")

        result = await int_repository.update(test_int_model)

        assert result is test_int_model
        mock_add.assert_called_once_with(test_int_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_int_model)

    @pytest.mark.asyncio
    async def test_updates_uuid_entity_successfully(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        test_uuid_model: SampleUUIDModel,
        mocker: MockerFixture,
    ) -> None:
        """Test successful UUID entity update."""
        mock_add = mocker.patch.object(uuid_repository._session, "add")
        mock_commit = mocker.patch.object(uuid_repository._session, "commit")
        mock_refresh = mocker.patch.object(uuid_repository._session, "refresh")

        result = await uuid_repository.update(test_uuid_model)

        assert result is test_uuid_model
        mock_add.assert_called_once_with(test_uuid_model)
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once_with(test_uuid_model)


class TestBaseRepositoryDelete:
    """Test suite for BaseRepository.delete method."""

    @pytest.mark.asyncio
    async def test_deletes_existing_entity_successfully(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        test_int_model: SampleIntModel,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful entity deletion."""
        mock_session.get.return_value = test_int_model

        await int_repository.delete(1)

        mock_session.get.assert_called_once_with(SampleIntModel, 1)
        mock_session.delete.assert_called_once_with(test_int_model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deletes_existing_uuid_entity_successfully(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        test_uuid_model: SampleUUIDModel,
        sample_uuid: UUID,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful UUID entity deletion."""
        mock_session.get.return_value = test_uuid_model

        await uuid_repository.delete(sample_uuid)

        mock_session.get.assert_called_once_with(SampleUUIDModel, sample_uuid)
        mock_session.delete.assert_called_once_with(test_uuid_model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_entity_not_found_error_when_deleting_nonexistent(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test EntityNotFoundError for non-existent entity deletion."""
        mock_session.get.return_value = None

        with pytest.raises(EntityNotFoundError) as exc_info:
            await int_repository.delete(999)

        assert "SampleIntModel with ID 999 not found" in str(exc_info.value)
        mock_session.get.assert_called_once_with(SampleIntModel, 999)

    @pytest.mark.asyncio
    async def test_raises_entity_not_found_error_for_uuid_entity(
        self,
        uuid_repository: BaseRepository[SampleUUIDModel, UUID],
        sample_uuid: UUID,
        mock_session: AsyncMock,
    ) -> None:
        """Test EntityNotFoundError for non-existent UUID entity."""
        mock_session.get.return_value = None

        with pytest.raises(EntityNotFoundError) as exc_info:
            await uuid_repository.delete(sample_uuid)

        assert f"SampleUUIDModel with ID {sample_uuid!r} not found" in str(
            exc_info.value
        )
        mock_session.get.assert_called_once_with(SampleUUIDModel, sample_uuid)

    @pytest.mark.asyncio
    async def test_does_not_call_delete_when_entity_not_found(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test that delete is not called when entity doesn't exist."""
        mock_session.get.return_value = None

        with pytest.raises(EntityNotFoundError):
            await int_repository.delete(999)

        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()


class TestBaseRepositoryFilter:
    """Test suite for BaseRepository.filter method."""

    @pytest.mark.asyncio
    async def test_filters_entities_with_single_condition(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with single condition."""
        mock_models = [SampleIntModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test Model")
        results = await int_repository.filter(condition)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_entities_with_multiple_conditions(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with multiple conditions."""
        mock_models = [SampleIntModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition1 = cast(ColumnElement[bool], SampleIntModel.name == "Test Model")
        condition2 = cast(ColumnElement[bool], SampleIntModel.id == 1)
        results = await int_repository.filter(condition1, condition2)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_matches(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return when no entities match."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Nonexistent")
        results = await int_repository.filter(condition)

        assert results == []

    @pytest.mark.asyncio
    async def test_generates_select_statement_with_where_clause(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test that select statement includes where clause."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test")
        await int_repository.filter(condition)

        call_args = mock_session.exec.call_args[0][0]
        assert str(call_args).startswith("SELECT")


class TestBaseRepositoryFilterPaginated:
    """Test suite for BaseRepository.filter_paginated method."""

    @pytest.mark.asyncio
    async def test_filters_and_paginates_entities_successfully(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful filtering with pagination."""
        mock_models = [SampleIntModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test Model")
        results = await int_repository.filter_paginated(condition, limit=10, offset=5)

        assert results == mock_models
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_applies_default_offset_in_filtered_pagination(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test default offset application in filtered pagination."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test")
        await int_repository.filter_paginated(condition, limit=10)

        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_with_multiple_conditions_and_pagination(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test filtering with multiple conditions and pagination."""
        mock_models = [SampleIntModel(id=1, name="Test Model")]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_models
        mock_session.exec.return_value = mock_result

        condition1 = cast(ColumnElement[bool], SampleIntModel.name == "Test Model")
        condition2 = cast(ColumnElement[bool], SampleIntModel.id == 1)
        results = await int_repository.filter_paginated(
            condition1, condition2, limit=5, offset=10
        )

        assert results == mock_models

    @pytest.mark.parametrize(
        "limit", [0, -1, -100], ids=["zero_limit", "negative_one", "large_negative"]
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_limit_in_filter(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        limit: int,
    ) -> None:
        """Test InvalidPaginationError for invalid limit in filtered pagination."""
        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test")

        with pytest.raises(InvalidPaginationError):
            await int_repository.filter_paginated(condition, limit=limit)

    @pytest.mark.parametrize(
        "offset",
        [-1, -5, -100],
        ids=["negative_one", "negative_small", "negative_large"],
    )
    @pytest.mark.asyncio
    async def test_raises_invalid_pagination_error_for_invalid_offset_in_filter(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        offset: int,
    ) -> None:
        """Test InvalidPaginationError for invalid offset in filtered pagination."""
        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test")

        with pytest.raises(InvalidPaginationError):
            await int_repository.filter_paginated(condition, limit=10, offset=offset)

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_filtered_pagination_no_matches(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test empty list return for filtered pagination with no matches."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Nonexistent")
        results = await int_repository.filter_paginated(condition, limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_generates_complex_statement_with_where_offset_limit(
        self,
        int_repository: BaseRepository[SampleIntModel, int],
        mock_session: AsyncMock,
    ) -> None:
        """Test that statement includes where, offset, and limit clauses."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.exec.return_value = mock_result

        condition = cast(ColumnElement[bool], SampleIntModel.name == "Test")
        await int_repository.filter_paginated(condition, limit=10, offset=5)

        call_args = mock_session.exec.call_args[0][0]
        statement_str = str(call_args)
        assert statement_str.startswith("SELECT")
