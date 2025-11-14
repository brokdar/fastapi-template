"""Integration tests for BaseRepository with real PostgreSQL database."""

from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.exceptions import (
    EntityNotFoundError,
    RepositoryIntegrityError,
)
from app.core.pagination.exceptions import InvalidPaginationError

from .conftest import (
    ArticleModel,
    CustomerModel,
    OrderModel,
    ProductModel,
)


class TestBaseRepositoryGetById:
    """Test suite for get_by_id method with int and UUID types."""

    async def test_retrieves_product_by_int_id_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test retrieving existing product by int ID."""
        assert created_product.id is not None

        retrieved = await product_repository.get_by_id(created_product.id)

        assert retrieved is not None
        assert retrieved.id == created_product.id
        assert retrieved.name == created_product.name
        assert retrieved.price == created_product.price
        assert retrieved.category == created_product.category
        assert retrieved.in_stock == created_product.in_stock

    async def test_retrieves_article_by_uuid_id_successfully(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        created_article: ArticleModel,
    ) -> None:
        """Test retrieving existing article by UUID."""
        assert created_article.id is not None

        retrieved = await article_repository.get_by_id(created_article.id)

        assert retrieved is not None
        assert retrieved.id == created_article.id
        assert retrieved.title == created_article.title
        assert retrieved.content == created_article.content
        assert retrieved.author == created_article.author
        assert retrieved.published == created_article.published

    async def test_returns_none_for_nonexistent_int_id(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test non-existent int ID returns None."""
        retrieved = await product_repository.get_by_id(999999)

        assert retrieved is None

    async def test_returns_none_for_nonexistent_uuid_id(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        sample_uuid_1: UUID,
    ) -> None:
        """Test non-existent UUID returns None."""
        retrieved = await article_repository.get_by_id(sample_uuid_1)

        assert retrieved is None

    async def test_retrieves_correct_product_among_multiple(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test correct entity retrieved when multiple exist."""
        target_product = multiple_products[10]
        assert target_product.id is not None

        retrieved = await product_repository.get_by_id(target_product.id)

        assert retrieved is not None
        assert retrieved.id == target_product.id
        assert retrieved.name == target_product.name


class TestBaseRepositoryGetAll:
    """Test suite for get_all method."""

    async def test_retrieves_all_products_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test retrieving all products."""
        all_products = await product_repository.get_all()

        assert len(all_products) >= len(multiple_products)
        product_ids = {p.id for p in all_products}
        for product in multiple_products:
            assert product.id in product_ids

    async def test_retrieves_all_articles_successfully(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        multiple_articles: list[ArticleModel],
    ) -> None:
        """Test retrieving all articles."""
        all_articles = await article_repository.get_all()

        assert len(all_articles) >= len(multiple_articles)
        article_ids = {a.id for a in all_articles}
        for article in multiple_articles:
            assert article.id in article_ids

    async def test_returns_empty_list_when_no_entities(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
    ) -> None:
        """Test empty table returns empty list."""
        all_customers = await customer_repository.get_all()

        assert all_customers == []

    async def test_retrieves_correct_count_with_multiple_entities(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test correct count when populated."""
        all_products = await product_repository.get_all()

        assert len(all_products) == len(multiple_products)


class TestBaseRepositoryCount:
    """Test suite for count method."""

    async def test_returns_zero_for_empty_table(
        self,
        order_repository: BaseRepository[OrderModel, int],
    ) -> None:
        """Test count is 0 for empty table."""
        count = await order_repository.count()

        assert count == 0

    @pytest.mark.usefixtures("created_product")
    async def test_returns_correct_count_for_single_entity(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test count is 1 after creating one."""
        count = await product_repository.count()

        assert count == 1

    async def test_returns_correct_count_for_multiple_entities(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test accurate count for multiple entities."""
        count = await product_repository.count()

        assert count == len(multiple_products)

    async def test_count_reflects_deletions(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test count decreases after deletion."""
        initial_count = await product_repository.count()
        first_product = multiple_products[0]
        assert first_product.id is not None

        await product_repository.delete(first_product.id)
        new_count = await product_repository.count()

        assert new_count == initial_count - 1


class TestBaseRepositoryGetPaginated:
    """Test suite for get_paginated method with various parameters."""

    @pytest.mark.usefixtures("multiple_products")
    async def test_retrieves_first_page_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test retrieving first page with offset=0, limit=10."""
        paginated = await product_repository.get_paginated(offset=0, limit=10)

        assert len(paginated) == 10
        assert all(isinstance(p, ProductModel) for p in paginated)

    @pytest.mark.usefixtures("multiple_products")
    async def test_retrieves_middle_page_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test retrieving middle page with offset=10, limit=10."""
        paginated = await product_repository.get_paginated(offset=10, limit=10)

        assert len(paginated) == 10

    @pytest.mark.usefixtures("multiple_products")
    async def test_retrieves_last_page_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test retrieving last page with partial results."""
        paginated = await product_repository.get_paginated(offset=20, limit=10)

        assert len(paginated) == 5

    @pytest.mark.usefixtures("multiple_products")
    async def test_retrieves_single_item_page(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test retrieving single item with offset=0, limit=1."""
        paginated = await product_repository.get_paginated(offset=0, limit=1)

        assert len(paginated) == 1

    @pytest.mark.usefixtures("multiple_products")
    async def test_handles_offset_beyond_total_count(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test offset beyond total count returns empty results."""
        paginated = await product_repository.get_paginated(offset=100, limit=10)

        assert paginated == []

    @pytest.mark.usefixtures("multiple_products")
    async def test_applies_default_parameters(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test default parameters (offset=0, limit=10)."""
        paginated = await product_repository.get_paginated()

        assert len(paginated) == 10

    @pytest.mark.usefixtures("multiple_products")
    async def test_raises_invalid_pagination_error_for_zero_limit(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test limit=0 raises InvalidPaginationError."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'limit'.*must be positive integer",
        ):
            await product_repository.get_paginated(offset=0, limit=0)

    @pytest.mark.usefixtures("multiple_products")
    async def test_raises_invalid_pagination_error_for_negative_limit(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test limit=-1 raises InvalidPaginationError."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'limit'.*must be positive integer",
        ):
            await product_repository.get_paginated(offset=0, limit=-1)

    @pytest.mark.usefixtures("multiple_products")
    async def test_raises_invalid_pagination_error_for_negative_offset(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test offset=-1 raises InvalidPaginationError."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await product_repository.get_paginated(offset=-1, limit=10)

    @pytest.mark.usefixtures("multiple_products")
    @pytest.mark.parametrize(
        "invalid_limit",
        ["10", 3.14],
        ids=["string_limit", "float_limit"],
    )
    async def test_raises_invalid_pagination_error_for_non_integer_limit(
        self,
        product_repository: BaseRepository[ProductModel, int],
        invalid_limit: Any,
    ) -> None:
        """Test non-integer limit raises InvalidPaginationError."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'limit'.*must be positive integer",
        ):
            await product_repository.get_paginated(offset=0, limit=invalid_limit)

    @pytest.mark.usefixtures("multiple_products")
    @pytest.mark.parametrize(
        "invalid_offset",
        ["5", 2.5],
        ids=["string_offset", "float_offset"],
    )
    async def test_raises_invalid_pagination_error_for_non_integer_offset(
        self,
        product_repository: BaseRepository[ProductModel, int],
        invalid_offset: Any,
    ) -> None:
        """Test non-integer offset raises InvalidPaginationError."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await product_repository.get_paginated(offset=invalid_offset, limit=10)


class TestBaseRepositoryCreate:
    """Test suite for create method."""

    async def test_creates_product_with_int_id_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
        sample_product_data: dict[str, Any],
    ) -> None:
        """Test creating int ID entity."""
        product = ProductModel(**sample_product_data)

        created = await product_repository.create(product)

        assert created.id is not None
        assert created.name == sample_product_data["name"]
        assert created.price == sample_product_data["price"]
        assert created.category == sample_product_data["category"]
        assert created.in_stock == sample_product_data["in_stock"]

    async def test_creates_article_with_uuid_id_successfully(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        sample_article_data: dict[str, Any],
    ) -> None:
        """Test creating UUID entity."""
        article = ArticleModel(**sample_article_data)

        created = await article_repository.create(article)

        assert created.id is not None
        assert isinstance(created.id, UUID)
        assert created.title == sample_article_data["title"]
        assert created.content == sample_article_data["content"]
        assert created.author == sample_article_data["author"]
        assert created.published == sample_article_data["published"]

    async def test_generates_int_id_automatically(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test auto-incremented ID assigned."""
        product = ProductModel(
            name="Auto ID Product",
            price=49.99,
            category="Test",
            in_stock=True,
        )

        created = await product_repository.create(product)

        assert created.id is not None
        assert isinstance(created.id, int)
        assert created.id > 0

    async def test_generates_uuid_automatically(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
    ) -> None:
        """Test UUID generated when not provided."""
        article = ArticleModel(
            title="Auto UUID Article",
            content="Test content",
            author="Test Author",
            published=False,
        )

        created = await article_repository.create(article)

        assert created.id is not None
        assert isinstance(created.id, UUID)

    async def test_persists_all_field_values_correctly(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test all fields saved to database."""
        product = ProductModel(
            name="Complete Product",
            price=199.99,
            category="Premium",
            in_stock=False,
        )

        created = await product_repository.create(product)
        assert created.id is not None

        retrieved = await product_repository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.name == "Complete Product"
        assert retrieved.price == 199.99
        assert retrieved.category == "Premium"
        assert retrieved.in_stock is False

    async def test_created_entity_retrievable_by_id(
        self,
        product_repository: BaseRepository[ProductModel, int],
        sample_product_data: dict[str, Any],
    ) -> None:
        """Test created entity can be fetched by ID."""
        product = ProductModel(**sample_product_data)

        created = await product_repository.create(product)
        assert created.id is not None

        retrieved = await product_repository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    async def test_raises_integrity_error_for_duplicate_unique_field(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
        created_customer: CustomerModel,
    ) -> None:
        """Test unique constraint violation."""
        duplicate_customer = CustomerModel(
            email=created_customer.email,
            username="different_username",
            full_name="Different Name",
        )

        with pytest.raises(
            RepositoryIntegrityError,
            match="Integrity constraint violation.*unique",
        ):
            await customer_repository.create(duplicate_customer)

    async def test_raises_integrity_error_for_null_required_field(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test NOT NULL constraint violation."""
        invalid_product = ProductModel(name="Test", price=10.0)
        object.__setattr__(invalid_product, "name", None)

        with pytest.raises(
            RepositoryIntegrityError,
            match="Integrity constraint violation",
        ):
            await product_repository.create(invalid_product)


class TestBaseRepositoryUpdate:
    """Test suite for update method."""

    async def test_updates_product_fields_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test updating int ID entity fields."""
        created_product.name = "Updated Product"
        created_product.price = 149.99

        updated = await product_repository.update(created_product)

        assert updated.name == "Updated Product"
        assert updated.price == 149.99

    async def test_updates_article_fields_successfully(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        created_article: ArticleModel,
    ) -> None:
        """Test updating UUID entity fields."""
        created_article.title = "Updated Article"
        created_article.published = True

        updated = await article_repository.update(created_article)

        assert updated.title == "Updated Article"
        assert updated.published is True

    async def test_update_persists_to_database(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test changes visible in subsequent queries."""
        created_product.name = "Persisted Update"

        await product_repository.update(created_product)
        assert created_product.id is not None

        retrieved = await product_repository.get_by_id(created_product.id)

        assert retrieved is not None
        assert retrieved.name == "Persisted Update"

    async def test_updates_single_field_without_affecting_others(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test partial update."""
        original_category = created_product.category
        created_product.name = "Only Name Changed"

        updated = await product_repository.update(created_product)

        assert updated.name == "Only Name Changed"
        assert updated.category == original_category

    async def test_updates_nullable_field_to_null(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test setting field to None."""
        created_product.category = None

        updated = await product_repository.update(created_product)

        assert updated.category is None

    async def test_updates_nullable_field_from_null(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
    ) -> None:
        """Test setting None field to value."""
        article = ArticleModel(
            title="Test Article",
            content="Content",
            author=None,
            published=False,
        )
        created = await article_repository.create(article)

        created.author = "New Author"
        updated = await article_repository.update(created)

        assert updated.author == "New Author"

    async def test_raises_integrity_error_for_unique_constraint_on_update(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
    ) -> None:
        """Test update causes unique violation."""
        customer1 = CustomerModel(
            email="customer1@example.com",
            username="customer1",
            full_name="Customer One",
        )
        customer2 = CustomerModel(
            email="customer2@example.com",
            username="customer2",
            full_name="Customer Two",
        )
        created1 = await customer_repository.create(customer1)
        created2 = await customer_repository.create(customer2)

        created2.email = created1.email

        with pytest.raises(
            RepositoryIntegrityError,
            match="Integrity constraint violation.*unique",
        ):
            await customer_repository.update(created2)


class TestBaseRepositoryDelete:
    """Test suite for delete method."""

    async def test_deletes_product_by_int_id_successfully(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test deleting int ID entity."""
        assert created_product.id is not None

        await product_repository.delete(created_product.id)

        retrieved = await product_repository.get_by_id(created_product.id)
        assert retrieved is None

    async def test_deletes_article_by_uuid_id_successfully(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        created_article: ArticleModel,
    ) -> None:
        """Test deleting UUID entity."""
        assert created_article.id is not None

        await article_repository.delete(created_article.id)

        retrieved = await article_repository.get_by_id(created_article.id)
        assert retrieved is None

    async def test_deleted_entity_no_longer_retrievable(
        self,
        product_repository: BaseRepository[ProductModel, int],
        created_product: ProductModel,
    ) -> None:
        """Test get_by_id returns None after deletion."""
        assert created_product.id is not None

        await product_repository.delete(created_product.id)

        retrieved = await product_repository.get_by_id(created_product.id)
        assert retrieved is None

    async def test_count_decreases_after_deletion(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test count reflects deletion."""
        initial_count = await product_repository.count()
        first_product = multiple_products[0]
        assert first_product.id is not None

        await product_repository.delete(first_product.id)

        new_count = await product_repository.count()
        assert new_count == initial_count - 1

    async def test_raises_entity_not_found_error_for_nonexistent_int_id(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test deleting non-existent int ID."""
        with pytest.raises(
            EntityNotFoundError,
            match="ProductModel with ID 999999 not found",
        ):
            await product_repository.delete(999999)

    async def test_raises_entity_not_found_error_for_nonexistent_uuid_id(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
        sample_uuid_1: UUID,
    ) -> None:
        """Test deleting non-existent UUID."""
        with pytest.raises(
            EntityNotFoundError,
            match=r"ArticleModel with ID UUID\('12345678-1234-5678-1234-567812345678'\) not found",
        ):
            await article_repository.delete(sample_uuid_1)

    async def test_raises_integrity_error_for_foreign_key_constraint(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
        order_repository: BaseRepository[OrderModel, int],
        created_customer: CustomerModel,
    ) -> None:
        """Test deleting referenced entity."""
        assert created_customer.id is not None
        order = OrderModel(
            customer_id=created_customer.id,
            total_amount=99.99,
            status="pending",
        )
        await order_repository.create(order)

        with pytest.raises(
            RepositoryIntegrityError,
            match="Integrity constraint violation.*foreign key",
        ):
            await customer_repository.delete(created_customer.id)


class TestBaseRepositoryFilter:
    """Test suite for filter method with various conditions."""

    async def test_filters_by_single_equality_condition(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test filtering with single equality condition."""
        target_product = multiple_products[5]

        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.name == target_product.name)
        )

        assert len(filtered) == 1
        assert filtered[0].name == target_product.name

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_by_single_inequality_condition(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering with inequality condition."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.price > 100)
        )

        assert all(p.price > 100 for p in filtered)
        assert len(filtered) > 0

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_by_multiple_conditions(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering with multiple AND conditions."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            cast(ColumnElement[bool], ProductModel.in_stock == True),  # noqa: E712
        )

        assert all(p.category == "Cat A" for p in filtered)
        assert all(p.in_stock is True for p in filtered)
        assert len(filtered) > 0

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_by_like_pattern(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering with LIKE pattern."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], col(ProductModel.name).like("%Product 1%"))
        )

        assert all("1" in p.name for p in filtered)
        assert len(filtered) > 0

    async def test_filters_by_null_value(
        self,
        article_repository: BaseRepository[ArticleModel, UUID],
    ) -> None:
        """Test filtering for null values."""
        article = ArticleModel(
            title="No Author Article",
            content="Content",
            author=None,
            published=False,
        )
        await article_repository.create(article)

        filtered = await article_repository.filter(
            cast(ColumnElement[bool], col(ArticleModel.author).is_(None))
        )

        assert all(a.author is None for a in filtered)
        assert len(filtered) >= 1

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_by_boolean_field(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering by boolean field."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.in_stock == False)  # noqa: E712
        )

        assert all(p.in_stock is False for p in filtered)
        assert len(filtered) > 0

    @pytest.mark.usefixtures("multiple_products")
    async def test_returns_empty_list_when_no_matches(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test no entities match filter."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.name == "Nonexistent Product")
        )

        assert filtered == []

    async def test_returns_all_matching_entities(
        self,
        product_repository: BaseRepository[ProductModel, int],
        multiple_products: list[ProductModel],
    ) -> None:
        """Test multiple entities match filter."""
        filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.category == "Cat A")
        )

        expected_count = sum(1 for p in multiple_products if p.category == "Cat A")
        assert len(filtered) == expected_count
        assert all(p.category == "Cat A" for p in filtered)


class TestBaseRepositoryFilterPaginated:
    """Test suite for filter_paginated method."""

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_and_paginates_first_page(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering with first page pagination."""
        filtered = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            limit=5,
            offset=0,
        )

        assert len(filtered) <= 5
        assert all(p.category == "Cat A" for p in filtered)

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_and_paginates_middle_page(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filtering with middle page pagination."""
        filtered = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            limit=5,
            offset=5,
        )

        assert len(filtered) <= 5
        assert all(p.category == "Cat A" for p in filtered)

    @pytest.mark.usefixtures("multiple_products")
    async def test_filters_with_multiple_conditions_and_pagination(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test complex filter with pagination."""
        filtered = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            cast(ColumnElement[bool], ProductModel.in_stock == True),  # noqa: E712
            limit=3,
            offset=0,
        )

        assert len(filtered) <= 3
        assert all(p.category == "Cat A" for p in filtered)
        assert all(p.in_stock is True for p in filtered)

    @pytest.mark.usefixtures("multiple_products")
    async def test_pagination_applies_to_filtered_results_only(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test offset/limit based on filtered set."""
        all_filtered = await product_repository.filter(
            cast(ColumnElement[bool], ProductModel.category == "Cat A")
        )

        first_page = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            limit=5,
            offset=0,
        )
        second_page = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            limit=5,
            offset=5,
        )

        assert len(first_page) + len(second_page) <= len(all_filtered)
        if first_page and second_page:
            page1_ids = {p.id for p in first_page}
            page2_ids = {p.id for p in second_page}
            assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.usefixtures("multiple_products")
    async def test_returns_empty_list_when_filtered_results_exhausted(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test offset beyond filtered count."""
        filtered = await product_repository.filter_paginated(
            cast(ColumnElement[bool], ProductModel.category == "Cat A"),
            limit=10,
            offset=100,
        )

        assert filtered == []

    @pytest.mark.usefixtures("multiple_products")
    async def test_raises_invalid_pagination_error_for_invalid_limit_with_filter(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filter with limit=0 raises error."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'limit'.*must be positive integer",
        ):
            await product_repository.filter_paginated(
                cast(ColumnElement[bool], ProductModel.category == "Cat A"),
                limit=0,
                offset=0,
            )

    @pytest.mark.usefixtures("multiple_products")
    async def test_raises_invalid_pagination_error_for_invalid_offset_with_filter(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test filter with offset=-1 raises error."""
        with pytest.raises(
            InvalidPaginationError,
            match="Invalid pagination parameter 'offset'.*must be non-negative integer",
        ):
            await product_repository.filter_paginated(
                cast(ColumnElement[bool], ProductModel.category == "Cat A"),
                limit=5,
                offset=-1,
            )


class TestBaseRepositoryTransactionIsolation:
    """Test suite for transaction isolation validation."""

    async def test_changes_not_visible_across_test_functions(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test each test gets clean state."""
        count = await product_repository.count()

        assert count == 0

    async def test_rollback_occurs_after_test_completion(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test transaction rollback."""
        product = ProductModel(
            name="Temporary Product",
            price=99.99,
            category="Test",
            in_stock=True,
        )
        await product_repository.create(product)

        count = await product_repository.count()
        assert count == 1

    async def test_each_test_starts_with_clean_database(
        self,
        product_repository: BaseRepository[ProductModel, int],
    ) -> None:
        """Test no residual data from previous tests."""
        all_products = await product_repository.get_all()

        assert all_products == []


class TestBaseRepositoryErrorHandling:
    """Test suite for repository error decorator functionality."""

    async def test_integrity_error_converted_to_repository_integrity_error(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
    ) -> None:
        """Test unique constraint violation conversion."""
        customer1 = CustomerModel(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
        )
        await customer_repository.create(customer1)

        customer2 = CustomerModel(
            email="test@example.com",
            username="different",
            full_name="Different User",
        )

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await customer_repository.create(customer2)

        assert "CustomerModel" in str(exc_info.value)

    async def test_error_includes_entity_type_in_message(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
    ) -> None:
        """Test error message contains model name."""
        customer1 = CustomerModel(
            email="error@example.com",
            username="erroruser",
            full_name="Error User",
        )
        await customer_repository.create(customer1)

        customer2 = CustomerModel(
            email="error@example.com",
            username="different2",
            full_name="Different User",
        )

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await customer_repository.create(customer2)

        assert "CustomerModel" in str(exc_info.value)

    async def test_error_includes_operation_context(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
    ) -> None:
        """Test error message contains operation name."""
        customer1 = CustomerModel(
            email="operation@example.com",
            username="opuser",
            full_name="Operation User",
        )
        await customer_repository.create(customer1)

        customer2 = CustomerModel(
            email="operation@example.com",
            username="different3",
            full_name="Different User",
        )

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await customer_repository.create(customer2)

        error_details = exc_info.value.details
        assert error_details is not None
        assert "entity_type" in error_details

    async def test_foreign_key_violation_converted_to_repository_integrity_error(
        self,
        customer_repository: BaseRepository[CustomerModel, int],
        order_repository: BaseRepository[OrderModel, int],
        created_customer: CustomerModel,
    ) -> None:
        """Test FK constraint violation conversion."""
        assert created_customer.id is not None
        order = OrderModel(
            customer_id=created_customer.id,
            total_amount=100.0,
            status="pending",
        )
        await order_repository.create(order)

        with pytest.raises(RepositoryIntegrityError) as exc_info:
            await customer_repository.delete(created_customer.id)

        assert "foreign key" in str(exc_info.value).lower()
