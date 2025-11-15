"""Test fixtures for base repository integration tests."""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.models import IntModel, UUIDModel
from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.bulk import BulkOperationsMixin


class ProductModel(IntModel, table=True):
    """Test model with integer ID for integration testing."""

    __tablename__ = "test_products"
    __table_args__ = {"extend_existing": True}

    name: str
    price: float
    category: str | None = Field(default=None)
    in_stock: bool = Field(default=True)


class ArticleModel(UUIDModel, table=True):
    """Test model with UUID ID for integration testing."""

    __tablename__ = "test_articles"
    __table_args__ = {"extend_existing": True}

    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(unique=True)
    content: str
    author: str | None = Field(default=None)
    published: bool = Field(default=False)


class CustomerModel(IntModel, table=True):
    """Test model with unique constraint for integrity testing."""

    __tablename__ = "test_customers"
    __table_args__ = (
        UniqueConstraint("email", "username", name="uq_customer_email_username"),
        {"extend_existing": True},
    )

    email: str = Field(unique=True)
    username: str = Field(unique=True)
    full_name: str


class OrderModel(IntModel, table=True):
    """Test model with foreign key for relationship testing."""

    __tablename__ = "test_orders"
    __table_args__ = {"extend_existing": True}

    customer_id: int = Field(foreign_key="test_customers.id")
    total_amount: float
    status: str = Field(default="pending")


class IntRepositoryWithBulk(
    BaseRepository[ProductModel, int], BulkOperationsMixin[ProductModel, int]
):
    """Repository combining BaseRepository with BulkOperationsMixin for int IDs."""


class UUIDRepositoryWithBulk(
    BaseRepository[ArticleModel, UUID], BulkOperationsMixin[ArticleModel, UUID]
):
    """Repository combining BaseRepository with BulkOperationsMixin for UUID IDs."""


class CustomerRepositoryWithBulk(
    BaseRepository[CustomerModel, int], BulkOperationsMixin[CustomerModel, int]
):
    """Repository with bulk operations for CustomerModel with unique constraints."""


@pytest.fixture(autouse=True)
async def cleanup_test_tables(
    test_engine: AsyncEngine,
) -> AsyncGenerator[None, None]:
    """Drop test tables after each test to prevent schema conflicts."""
    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: OrderModel.metadata.tables[OrderModel.__tablename__].drop(
                sync_conn, checkfirst=True
            )
        )
        await conn.run_sync(
            lambda sync_conn: CustomerModel.metadata.tables[
                CustomerModel.__tablename__
            ].drop(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: ArticleModel.metadata.tables[
                ArticleModel.__tablename__
            ].drop(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: ProductModel.metadata.tables[
                ProductModel.__tablename__
            ].drop(sync_conn, checkfirst=True)
        )


@pytest.fixture
async def product_repository(
    test_session: AsyncSession,
) -> BaseRepository[ProductModel, int]:
    """Provide BaseRepository for ProductModel."""
    return BaseRepository[ProductModel, int](test_session, ProductModel)


@pytest.fixture
async def article_repository(
    test_session: AsyncSession,
) -> BaseRepository[ArticleModel, UUID]:
    """Provide BaseRepository for ArticleModel."""
    return BaseRepository[ArticleModel, UUID](test_session, ArticleModel)


@pytest.fixture
async def customer_repository(
    test_session: AsyncSession,
) -> BaseRepository[CustomerModel, int]:
    """Provide BaseRepository for CustomerModel."""
    return BaseRepository[CustomerModel, int](test_session, CustomerModel)


@pytest.fixture
async def order_repository(
    test_session: AsyncSession,
) -> BaseRepository[OrderModel, int]:
    """Provide BaseRepository for OrderModel."""
    return BaseRepository[OrderModel, int](test_session, OrderModel)


@pytest.fixture
async def int_bulk_repository(
    test_session: AsyncSession,
) -> IntRepositoryWithBulk:
    """Provide repository with bulk operations for ProductModel."""
    return IntRepositoryWithBulk(test_session, ProductModel)


@pytest.fixture
async def uuid_bulk_repository(
    test_session: AsyncSession,
) -> UUIDRepositoryWithBulk:
    """Provide repository with bulk operations for ArticleModel."""
    return UUIDRepositoryWithBulk(test_session, ArticleModel)


@pytest.fixture
async def customer_bulk_repository(
    test_session: AsyncSession,
) -> CustomerRepositoryWithBulk:
    """Provide repository with bulk operations for CustomerModel."""
    return CustomerRepositoryWithBulk(test_session, CustomerModel)


@pytest.fixture
def sample_product_data() -> dict[str, Any]:
    """Provide sample product data."""
    return {
        "name": "Test Product",
        "price": 99.99,
        "category": "Electronics",
        "in_stock": True,
    }


@pytest.fixture
def sample_article_data() -> dict[str, Any]:
    """Provide sample article data."""
    return {
        "title": "Test Article",
        "content": "This is test content",
        "author": "Test Author",
        "published": False,
    }


@pytest.fixture
def sample_customer_data() -> dict[str, Any]:
    """Provide sample customer data."""
    return {
        "email": "customer@example.com",
        "username": "testcustomer",
        "full_name": "Test Customer",
    }


@pytest.fixture
async def created_product(
    product_repository: BaseRepository[ProductModel, int],
    sample_product_data: dict[str, Any],
) -> ProductModel:
    """Provide a pre-created product for tests."""
    product = ProductModel(**sample_product_data)
    return await product_repository.create(product)


@pytest.fixture
async def created_article(
    article_repository: BaseRepository[ArticleModel, UUID],
    sample_article_data: dict[str, Any],
) -> ArticleModel:
    """Provide a pre-created article for tests."""
    article = ArticleModel(**sample_article_data)
    return await article_repository.create(article)


@pytest.fixture
async def created_customer(
    customer_repository: BaseRepository[CustomerModel, int],
    sample_customer_data: dict[str, Any],
) -> CustomerModel:
    """Provide a pre-created customer for tests."""
    customer = CustomerModel(**sample_customer_data)
    return await customer_repository.create(customer)


@pytest.fixture
async def multiple_products(
    product_repository: BaseRepository[ProductModel, int],
) -> list[ProductModel]:
    """Provide multiple products for pagination and filter testing."""
    products = [
        ProductModel(
            name=f"Product {i}",
            price=float(i * 10),
            category="Cat A" if i % 2 == 0 else "Cat B",
            in_stock=i % 3 != 0,
        )
        for i in range(1, 26)
    ]
    return [await product_repository.create(p) for p in products]


@pytest.fixture
async def multiple_articles(
    article_repository: BaseRepository[ArticleModel, UUID],
) -> list[ArticleModel]:
    """Provide multiple articles for pagination and filter testing."""
    articles = [
        ArticleModel(
            title=f"Article {i}",
            content=f"Content for article {i}",
            author="Author A" if i % 2 == 0 else "Author B",
            published=i % 3 == 0,
        )
        for i in range(1, 16)
    ]
    return [await article_repository.create(a) for a in articles]


@pytest.fixture
def sample_uuid_1() -> UUID:
    """Provide first sample UUID for testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_uuid_2() -> UUID:
    """Provide second sample UUID for testing."""
    return UUID("87654321-4321-8765-4321-876543218765")
