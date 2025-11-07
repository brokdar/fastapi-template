"""Test suite for BulkOperationsMixin."""

from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import exc as sqlalchemy_exc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.bulk import BulkOperationsMixin
from app.core.base.repositories.exceptions import RepositoryOperationError
from tests.unit.core.base.repositories.conftest import SampleIntModel, SampleUUIDModel


class IntRepositoryWithBulk(
    BaseRepository[SampleIntModel, int],
    BulkOperationsMixin[SampleIntModel, int],
):
    """Repository with bulk operations for testing with integer IDs."""


class UUIDRepositoryWithBulk(
    BaseRepository[SampleUUIDModel, UUID],
    BulkOperationsMixin[SampleUUIDModel, UUID],
):
    """Repository with bulk operations for testing with UUID IDs."""


@pytest.fixture
def int_bulk_repository(mock_session: AsyncSession) -> IntRepositoryWithBulk:
    """Provide IntRepositoryWithBulk instance."""
    return IntRepositoryWithBulk(mock_session, SampleIntModel)


@pytest.fixture
def uuid_bulk_repository(mock_session: AsyncSession) -> UUIDRepositoryWithBulk:
    """Provide UUIDRepositoryWithBulk instance."""
    return UUIDRepositoryWithBulk(mock_session, SampleUUIDModel)


@pytest.fixture
def sample_int_models() -> list[SampleIntModel]:
    """Provide list of sample int models for testing."""
    return [
        SampleIntModel(name="Model 1"),
        SampleIntModel(name="Model 2"),
        SampleIntModel(name="Model 3"),
    ]


@pytest.fixture
def sample_int_models_with_ids() -> list[SampleIntModel]:
    """Provide list of sample int models with IDs for testing."""
    return [
        SampleIntModel(id=1, name="Model 1"),
        SampleIntModel(id=2, name="Model 2"),
        SampleIntModel(id=3, name="Model 3"),
    ]


@pytest.fixture
def sample_uuid_models() -> list[SampleUUIDModel]:
    """Provide list of sample UUID models for testing."""
    return [
        SampleUUIDModel(name="UUID Model 1"),
        SampleUUIDModel(name="UUID Model 2"),
        SampleUUIDModel(name="UUID Model 3"),
    ]


class TestBulkCreate:
    """Test suite for BulkOperationsMixin.bulk_create method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk create with empty list returns empty list."""
        result = await int_bulk_repository.bulk_create([])

        assert result == []
        mock_session.scalars.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_single_item_successfully(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk create with single item."""
        item = SampleIntModel(name="Test Model")
        created_item = SampleIntModel(id=1, name="Test Model")

        mock_result = Mock()
        mock_result.all.return_value = [created_item]
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_create([item])

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "Test Model"

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_multiple_items_successfully(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk create with multiple items."""
        created_items = [
            SampleIntModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_int_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = created_items
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_create(sample_int_models)

        assert len(result) == 3
        for i, item in enumerate(result):
            assert item.id == i + 1
            assert item.name == f"Model {i + 1}"

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_none_ids_from_dictionaries(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test that bulk create filters out None IDs from model dictionaries."""
        items = [
            SampleIntModel(id=None, name="Model 1"),
            SampleIntModel(id=5, name="Model 2"),
        ]
        created_items = [
            SampleIntModel(id=1, name="Model 1"),
            SampleIntModel(id=5, name="Model 2"),
        ]

        mock_result = Mock()
        mock_result.all.return_value = created_items
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_create(items)

        assert len(result) == 2

        call_args = mock_session.scalars.call_args[0]
        item_dicts = call_args[1]

        assert "id" not in item_dicts[0]
        assert item_dicts[0]["name"] == "Model 1"

        assert item_dicts[1]["id"] == 5
        assert item_dicts[1]["name"] == "Model 2"

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk create are properly handled."""
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.scalars.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_create"):
            await int_bulk_repository.bulk_create(sample_int_models)


class TestBulkUpdate:
    """Test suite for BulkOperationsMixin.bulk_update method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk update with empty list returns empty list."""
        result = await int_bulk_repository.bulk_update([])

        assert result == []
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_value_error_when_items_missing_ids(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
    ) -> None:
        """Test that bulk update raises error for items without IDs."""
        with pytest.raises(ValueError, match="Cannot update SampleIntModel without ID"):
            await int_bulk_repository.bulk_update(sample_int_models)

    @pytest.mark.asyncio
    async def test_updates_items_successfully(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models_with_ids: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk update."""
        mock_result = Mock()
        mock_result.all.return_value = sample_int_models_with_ids
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_update(sample_int_models_with_ids)

        assert result == sample_int_models_with_ids

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models_with_ids: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk update are properly handled."""
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.scalars.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_update"):
            await int_bulk_repository.bulk_update(sample_int_models_with_ids)


class TestBulkDelete:
    """Test suite for BulkOperationsMixin.bulk_delete method."""

    @pytest.mark.asyncio
    async def test_performs_no_operation_when_empty_input(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk delete with empty list does nothing."""
        await int_bulk_repository.bulk_delete([])

        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_deletes_items_successfully(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk delete."""
        ids = [1, 2, 3, 4, 5]

        await int_bulk_repository.bulk_delete(ids)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
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
            await int_bulk_repository.bulk_delete(ids)


class TestBulkUpsert:
    """Test suite for BulkOperationsMixin.bulk_upsert method."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk upsert with empty list returns empty list."""
        result = await int_bulk_repository.bulk_upsert([], ["name"])

        assert result == []
        mock_session.scalars.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_upserts_with_default_update_columns_successfully(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk upsert with default update columns."""
        upserted_items = [
            SampleIntModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_int_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = upserted_items
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_upsert(
            sample_int_models, conflict_columns=["name"]
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
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test successful bulk upsert with specific update columns."""
        upserted_items = [
            SampleIntModel(id=i + 1, name=f"Model {i + 1}")
            for i in range(len(sample_int_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = upserted_items
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_upsert(
            sample_int_models,
            conflict_columns=["name"],
            update_columns=["name"],
        )

        assert len(result) == 3

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_filters_none_ids_from_dictionaries(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test that bulk upsert filters out None IDs from model dictionaries."""
        items = [
            SampleIntModel(id=None, name="Model 1"),
            SampleIntModel(id=5, name="Model 2"),
        ]
        upserted_items = [
            SampleIntModel(id=1, name="Model 1"),
            SampleIntModel(id=5, name="Model 2"),
        ]

        mock_result = Mock()
        mock_result.all.return_value = upserted_items
        mock_session.scalars.return_value = mock_result

        result = await int_bulk_repository.bulk_upsert(items, ["name"])

        assert len(result) == 2

        call_args = mock_session.scalars.call_args[0]
        item_dicts = call_args[1]

        assert "id" not in item_dicts[0]
        assert item_dicts[0]["name"] == "Model 1"

        assert item_dicts[1]["id"] == 5
        assert item_dicts[1]["name"] == "Model 2"

    @pytest.mark.asyncio
    async def test_raises_repository_error_when_database_fails(
        self,
        int_bulk_repository: IntRepositoryWithBulk,
        sample_int_models: list[SampleIntModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test that database errors during bulk upsert are properly handled."""
        original_exception = RuntimeError("Connection failed")
        database_error = sqlalchemy_exc.DatabaseError(
            "Database error", None, original_exception
        )

        mock_session.scalars.side_effect = database_error

        with pytest.raises(RepositoryOperationError, match="bulk_upsert"):
            await int_bulk_repository.bulk_upsert(sample_int_models, ["name"])


class TestBulkOperationsWithUUID:
    """Test suite for bulk operations with UUID models."""

    @pytest.mark.asyncio
    async def test_creates_uuid_models_successfully(
        self,
        uuid_bulk_repository: UUIDRepositoryWithBulk,
        sample_uuid_models: list[SampleUUIDModel],
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk create with UUID models."""
        created_items = [
            SampleUUIDModel(id=uuid4(), name=f"UUID Model {i + 1}")
            for i in range(len(sample_uuid_models))
        ]

        mock_result = Mock()
        mock_result.all.return_value = created_items
        mock_session.scalars.return_value = mock_result

        result = await uuid_bulk_repository.bulk_create(sample_uuid_models)

        assert len(result) == 3
        for item in result:
            assert item.id is not None
            assert isinstance(item.id, UUID)

        mock_session.scalars.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deletes_uuid_models_successfully(
        self,
        uuid_bulk_repository: UUIDRepositoryWithBulk,
        mock_session: AsyncMock,
    ) -> None:
        """Test bulk delete with UUID IDs."""
        uuids = [uuid4() for _ in range(3)]

        await uuid_bulk_repository.bulk_delete(uuids)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
