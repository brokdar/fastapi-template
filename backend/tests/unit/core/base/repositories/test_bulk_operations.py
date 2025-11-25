"""Test suite for BulkOperationsMixin."""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import exc as sqlalchemy_exc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.bulk import BulkOperationsMixin
from app.core.base.repositories.exceptions import RepositoryOperationError
from tests.unit.core.base.repositories.conftest import SampleModel


class RepositoryWithBulk(
    BaseRepository[SampleModel],
    BulkOperationsMixin[SampleModel],
):
    """Repository with bulk operations for testing."""


@pytest.fixture
def bulk_repository(mock_session: AsyncSession) -> RepositoryWithBulk:
    """Provide RepositoryWithBulk instance."""
    return RepositoryWithBulk(mock_session, SampleModel)


@pytest.fixture
def sample_models() -> list[SampleModel]:
    """Provide list of sample models for testing."""
    return [
        SampleModel(name="Model 1"),
        SampleModel(name="Model 2"),
        SampleModel(name="Model 3"),
    ]


@pytest.fixture
def sample_models_with_ids() -> list[SampleModel]:
    """Provide list of sample models with IDs for testing."""
    return [
        SampleModel(id=1, name="Model 1"),
        SampleModel(id=2, name="Model 2"),
        SampleModel(id=3, name="Model 3"),
    ]


class TestBulkCreate:
    """Test suite for BulkOperationsMixin.bulk_create method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk create with empty list returns empty list."""
        result = await bulk_repository.bulk_create([])

        assert result == []
        mock_session.scalars.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_single_item_successfully(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk create with single item."""
        item = SampleModel(name="Test Model")
        created_item = SampleModel(id=1, name="Test Model")

        mock_result = Mock()
        mock_result.all.return_value = [created_item]
        mock_session.scalars.return_value = mock_result

        result = await bulk_repository.bulk_create([item])

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Test Model"

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_multiple_items_successfully(
        self,
        bulk_repository: RepositoryWithBulk,
        sample_models: list[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk create with multiple items."""
        created_items = [
            SampleModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = created_items
        mock_session.scalars.return_value = mock_result

        result = await bulk_repository.bulk_create(sample_models)

        assert len(result) == 3
        for i, item in enumerate(result):
            assert item.id == i + 1
            assert item.name == f"Model {i + 1}"

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        bulk_repository: RepositoryWithBulk,
        sample_models: list[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk create are properly handled."""
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.scalars.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_create"):
            await bulk_repository.bulk_create(sample_models)


class TestBulkDelete:
    """Test suite for BulkOperationsMixin.bulk_delete method."""

    @pytest.mark.asyncio
    async def test_performs_no_operation_when_empty_input(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk delete with empty list does nothing."""
        await bulk_repository.bulk_delete([])

        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_items_successfully(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk delete."""
        ids = [1, 2, 3, 4, 5]

        await bulk_repository.bulk_delete(ids)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk delete are properly handled."""
        ids = [1, 2, 3]
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.execute.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_delete"):
            await bulk_repository.bulk_delete(ids)


class TestBulkUpsert:
    """Test suite for BulkOperationsMixin.bulk_upsert method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        bulk_repository: RepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk upsert with empty list returns empty list."""
        result = await bulk_repository.bulk_upsert([], ["name"])

        assert result == []
        mock_session.scalars.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_upserts_with_default_update_columns_successfully(
        self,
        bulk_repository: RepositoryWithBulk,
        sample_models: list[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk upsert with default update columns."""
        upserted_items = [
            SampleModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = upserted_items
        mock_session.scalars.return_value = mock_result

        result = await bulk_repository.bulk_upsert(
            sample_models, conflict_columns=["name"]
        )

        assert len(result) == 3
        for i, item in enumerate(result):
            assert item.id == i + 1
            assert item.name == f"Model {i + 1}"

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_upserts_with_specific_update_columns_successfully(
        self,
        bulk_repository: RepositoryWithBulk,
        sample_models: list[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk upsert with specific update columns."""
        upserted_items = [
            SampleModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = upserted_items
        mock_session.scalars.return_value = mock_result

        result = await bulk_repository.bulk_upsert(
            sample_models,
            conflict_columns=["name"],
            update_columns=["name"],
        )

        assert len(result) == 3

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        bulk_repository: RepositoryWithBulk,
        sample_models: list[SampleModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk upsert are properly handled."""
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.scalars.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_upsert"):
            await bulk_repository.bulk_upsert(sample_models, ["name"])
