"""Integration tests for BulkOperationsMixin."""

from typing import Any

import pytest

from app.core.base.repositories.exceptions import RepositoryIntegrityError
from tests.integration.core.base.repositories.conftest import (
    ArticleModel,
    ArticleRepositoryWithBulk,
    CustomerModel,
    CustomerRepositoryWithBulk,
    OrderModel,
    ProductModel,
    ProductRepositoryWithBulk,
)


class TestBulkCreate:
    """Test suite for bulk_create operation."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create returns empty list for empty input."""
        result = await product_bulk_repository.bulk_create([])

        assert result == []

    @pytest.mark.asyncio
    async def test_creates_single_item_with_generated_id(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create creates single item and generates ID."""
        product = ProductModel(
            name="Single Product",
            price=49.99,
            category="Test",
            in_stock=True,
        )

        result = await product_bulk_repository.bulk_create([product])

        assert len(result) == 1
        assert result[0].id is not None
        assert result[0].name == "Single Product"
        assert result[0].price == 49.99
        assert result[0].category == "Test"
        assert result[0].in_stock is True

    @pytest.mark.asyncio
    async def test_creates_multiple_items_with_generated_ids(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create creates multiple items with generated IDs."""
        products = [
            ProductModel(name=f"Product {i}", price=float(i * 10), in_stock=True)
            for i in range(1, 6)
        ]

        result = await product_bulk_repository.bulk_create(products)

        assert len(result) == 5
        for i, item in enumerate(result, start=1):
            assert item.id is not None
            assert item.name == f"Product {i}"
            assert item.price == float(i * 10)

    @pytest.mark.asyncio
    async def test_creates_large_batch_successfully(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create handles large batch of items."""
        products = [
            ProductModel(name=f"Bulk Product {i}", price=float(i), in_stock=i % 2 == 0)
            for i in range(1, 51)
        ]

        result = await product_bulk_repository.bulk_create(products)

        assert len(result) == 50
        assert all(item.id is not None for item in result)
        assert result[0].name == "Bulk Product 1"
        assert result[49].name == "Bulk Product 50"

    @pytest.mark.asyncio
    async def test_creates_items_without_ids_successfully(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create handles items without IDs."""
        products = [
            ProductModel(name="No ID 1", price=10.0, in_stock=True),
            ProductModel(name="No ID 2", price=20.0, in_stock=False),
        ]

        result = await product_bulk_repository.bulk_create(products)

        assert len(result) == 2
        assert result[0].id is not None
        assert result[1].id is not None
        assert result[0].id != result[1].id

    @pytest.mark.asyncio
    async def test_raises_integrity_error_when_unique_constraint_violated(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_create raises RepositoryIntegrityError for duplicate unique fields."""
        customers = [
            CustomerModel(
                email="duplicate@example.com",
                username="user1",
                full_name="User One",
            ),
            CustomerModel(
                email="duplicate@example.com",
                username="user2",
                full_name="User Two",
            ),
        ]

        with pytest.raises(
            RepositoryIntegrityError, match="Integrity constraint violation"
        ):
            await customer_bulk_repository.bulk_create(customers)

    @pytest.mark.asyncio
    async def test_creates_article_items_with_generated_ids(
        self,
        article_bulk_repository: ArticleRepositoryWithBulk,
    ) -> None:
        """Test bulk_create creates article items with generated IDs."""
        articles = [
            ArticleModel(
                title=f"Article {i}",
                content=f"Content {i}",
                author="Test Author",
                published=False,
            )
            for i in range(1, 4)
        ]

        result = await article_bulk_repository.bulk_create(articles)

        assert len(result) == 3
        for i, item in enumerate(result, start=1):
            assert item.id is not None
            assert isinstance(item.id, int)
            assert item.title == f"Article {i}"

    @pytest.mark.asyncio
    async def test_returns_items_with_all_fields_populated(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_create returns items with all fields from RETURNING clause."""
        products = [
            ProductModel(
                name="Full Fields",
                price=99.99,
                category="Electronics",
                in_stock=True,
            ),
        ]

        result = await product_bulk_repository.bulk_create(products)

        assert len(result) == 1
        item = result[0]
        assert item.id is not None
        assert item.name == "Full Fields"
        assert item.price == 99.99
        assert item.category == "Electronics"
        assert item.in_stock is True


class TestBulkDelete:
    """Test suite for bulk_delete operation."""

    @pytest.mark.asyncio
    async def test_does_nothing_when_empty_input(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete does nothing for empty input."""
        await product_bulk_repository.bulk_delete([])

        count = await product_bulk_repository.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_deletes_single_item_successfully(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete deletes single item successfully."""
        created = await product_bulk_repository.create(
            ProductModel(name="To Delete", price=10.0, in_stock=True)
        )
        assert created.id is not None

        await product_bulk_repository.bulk_delete([created.id])

        retrieved = await product_bulk_repository.get_by_id(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_deletes_multiple_items_successfully(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete deletes multiple items successfully."""
        products = [
            ProductModel(name=f"Product {i}", price=float(i * 10), in_stock=True)
            for i in range(1, 6)
        ]
        created = await product_bulk_repository.bulk_create(products)
        ids = [item.id for item in created if item.id is not None]
        assert len(ids) == 5

        await product_bulk_repository.bulk_delete(ids)

        for item_id in ids:
            retrieved = await product_bulk_repository.get_by_id(item_id)
            assert retrieved is None

    @pytest.mark.asyncio
    async def test_ignores_nonexistent_ids_silently(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete ignores non-existent IDs silently."""
        nonexistent_ids = [999, 1000, 1001]

        await product_bulk_repository.bulk_delete(nonexistent_ids)

        count = await product_bulk_repository.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_raises_integrity_error_when_foreign_key_constraint_violated(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
        order_repository: Any,
    ) -> None:
        """Test bulk_delete raises RepositoryIntegrityError for foreign key violations."""
        customer = await customer_bulk_repository.create(
            CustomerModel(
                email="customer@example.com",
                username="customer",
                full_name="Customer Name",
            )
        )
        assert customer.id is not None
        await order_repository.create(
            OrderModel(customer_id=customer.id, total_amount=100.0, status="pending")
        )

        with pytest.raises(
            RepositoryIntegrityError, match="Integrity constraint violation"
        ):
            await customer_bulk_repository.bulk_delete([customer.id])

    @pytest.mark.asyncio
    async def test_deletes_article_items_successfully(
        self,
        article_bulk_repository: ArticleRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete deletes article items successfully."""
        articles = [
            ArticleModel(
                title=f"Article {i}",
                content=f"Content {i}",
                author="Test Author",
                published=False,
            )
            for i in range(1, 4)
        ]
        created = await article_bulk_repository.bulk_create(articles)
        ids = [item.id for item in created if item.id is not None]
        assert len(ids) == 3

        await article_bulk_repository.bulk_delete(ids)

        for item_id in ids:
            retrieved = await article_bulk_repository.get_by_id(item_id)
            assert retrieved is None

    @pytest.mark.asyncio
    async def test_deletion_is_permanent(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_delete permanently removes items."""
        products = [
            ProductModel(name=f"Product {i}", price=float(i * 10), in_stock=True)
            for i in range(1, 6)
        ]
        created = await product_bulk_repository.bulk_create(products)
        ids = [item.id for item in created if item.id is not None]
        assert len(ids) == 5

        await product_bulk_repository.bulk_delete(ids)

        all_items = await product_bulk_repository.get_all()
        assert len(all_items) == 0


class TestBulkUpsert:
    """Test suite for bulk_upsert operation."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_input(
        self,
        product_bulk_repository: ProductRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert returns empty list for empty input."""
        result = await product_bulk_repository.bulk_upsert(
            [], conflict_columns=["name"]
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_inserts_new_items_when_no_conflicts(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert inserts new items when no conflicts exist."""
        customers = [
            CustomerModel(
                email=f"user{i}@example.com",
                username=f"user{i}",
                full_name=f"User {i}",
            )
            for i in range(1, 4)
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"]
        )

        assert len(result) == 3
        for i, item in enumerate(result, start=1):
            assert item.id is not None
            assert item.email == f"user{i}@example.com"
            assert item.username == f"user{i}"

    @pytest.mark.asyncio
    async def test_updates_existing_items_when_conflicts_detected(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert updates existing items when conflicts detected."""
        await customer_bulk_repository.create(
            CustomerModel(
                email="existing@example.com",
                username="olduser",
                full_name="Old Name",
            )
        )

        customers = [
            CustomerModel(
                email="existing@example.com",
                username="newuser",
                full_name="New Name",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"]
        )

        assert len(result) == 1
        assert result[0].email == "existing@example.com"
        assert result[0].username == "newuser"
        assert result[0].full_name == "New Name"

    @pytest.mark.asyncio
    async def test_handles_mixed_insert_and_update_operations(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert handles mix of insert and update in single operation."""
        await customer_bulk_repository.create(
            CustomerModel(
                email="existing@example.com",
                username="existing",
                full_name="Existing User",
            )
        )

        customers = [
            CustomerModel(
                email="existing@example.com",
                username="updated",
                full_name="Updated Existing",
            ),
            CustomerModel(
                email="new@example.com", username="newuser", full_name="New User"
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"]
        )

        assert len(result) == 2
        existing = next(r for r in result if r.email == "existing@example.com")
        new = next(r for r in result if r.email == "new@example.com")

        assert existing.username == "updated"
        assert existing.full_name == "Updated Existing"
        assert new.username == "newuser"
        assert new.full_name == "New User"

    @pytest.mark.asyncio
    async def test_handles_conflict_on_single_column(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert handles conflict on single column."""
        await customer_bulk_repository.create(
            CustomerModel(
                email="user@example.com",
                username="original",
                full_name="Original Name",
            )
        )

        customers = [
            CustomerModel(
                email="user@example.com",
                username="different",
                full_name="Updated Name",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"]
        )

        assert len(result) == 1
        assert result[0].email == "user@example.com"
        assert result[0].username == "different"
        assert result[0].full_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_handles_conflict_on_multiple_columns(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert handles conflict on multiple columns."""
        await customer_bulk_repository.create(
            CustomerModel(
                email="user@example.com",
                username="testuser",
                full_name="Original Name",
            )
        )

        customers = [
            CustomerModel(
                email="user@example.com",
                username="testuser",
                full_name="Updated Name",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email", "username"]
        )

        assert len(result) == 1
        assert result[0].email == "user@example.com"
        assert result[0].username == "testuser"
        assert result[0].full_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_uses_custom_update_columns(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert respects custom update_columns parameter."""
        await customer_bulk_repository.create(
            CustomerModel(
                email="user@example.com",
                username="original",
                full_name="Original Name",
            )
        )

        customers = [
            CustomerModel(
                email="user@example.com",
                username="newusername",
                full_name="New Name",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"], update_columns=["full_name"]
        )

        assert len(result) == 1
        assert result[0].email == "user@example.com"
        assert result[0].username == "original"
        assert result[0].full_name == "New Name"

    @pytest.mark.asyncio
    async def test_uses_all_fields_except_id_when_update_columns_none(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert updates all fields except ID when update_columns is None."""
        created = await customer_bulk_repository.create(
            CustomerModel(
                email="user@example.com",
                username="original",
                full_name="Original Name",
            )
        )

        customers = [
            CustomerModel(
                email="user@example.com",
                username="updated",
                full_name="Updated Name",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"], update_columns=None
        )

        assert len(result) == 1
        assert result[0].id == created.id
        assert result[0].email == "user@example.com"
        assert result[0].username == "updated"
        assert result[0].full_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_handles_edge_case_when_no_fields_to_update(
        self,
        article_bulk_repository: ArticleRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert handles edge case when conflict is on unique field."""
        await article_bulk_repository.create(
            ArticleModel(
                title="Existing Article",
                content="Original content",
                author="Original Author",
            )
        )

        articles = [
            ArticleModel(
                title="Existing Article",
                content="Updated content",
                author="Updated Author",
            ),
        ]

        result = await article_bulk_repository.bulk_upsert(
            articles, conflict_columns=["title"]
        )

        assert len(result) == 1
        assert result[0].title == "Existing Article"
        assert result[0].content == "Updated content"
        assert result[0].author == "Updated Author"

    @pytest.mark.asyncio
    async def test_verifies_on_conflict_do_update_behavior(
        self,
        customer_bulk_repository: CustomerRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert uses PostgreSQL ON CONFLICT DO UPDATE correctly."""
        original = await customer_bulk_repository.create(
            CustomerModel(
                email="test@example.com",
                username="original",
                full_name="Original User",
            )
        )

        customers = [
            CustomerModel(
                email="test@example.com",
                username="updated",
                full_name="Updated User",
            ),
        ]

        result = await customer_bulk_repository.bulk_upsert(
            customers, conflict_columns=["email"]
        )

        assert len(result) == 1
        assert result[0].id == original.id
        assert result[0].email == "test@example.com"
        assert result[0].username == "updated"
        assert result[0].full_name == "Updated User"

        count = await customer_bulk_repository.count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_upserts_article_items_successfully(
        self,
        article_bulk_repository: ArticleRepositoryWithBulk,
    ) -> None:
        """Test bulk_upsert works with article items."""
        created = await article_bulk_repository.create(
            ArticleModel(
                title="Existing Article",
                content="Original Content",
                author="Original Author",
                published=False,
            )
        )

        articles = [
            ArticleModel(
                title="Existing Article",
                content="Updated Content",
                author="Updated Author",
                published=True,
            ),
        ]

        result = await article_bulk_repository.bulk_upsert(
            articles, conflict_columns=["title"]
        )

        assert len(result) == 1
        assert result[0].id == created.id
        assert result[0].title == "Existing Article"
        assert result[0].content == "Updated Content"
        assert result[0].author == "Updated Author"
        assert result[0].published is True
