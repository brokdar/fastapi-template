"""Integration test fixtures and configuration."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.providers.jwt.schemas import TokenResponse
from app.db.session import get_session
from app.dependencies import get_auth_service, get_user_repository, password_service
from app.domains.users.models import User, UserRole
from app.domains.users.schemas import UserCreate
from app.domains.users.services import UserService
from app.main import app
from tests.integration import IntegrationSettings

AuthenticatedClientFactory = Callable[
    [dict[str, str]], AsyncGenerator[httpx.AsyncClient, None]
]


@pytest.fixture(scope="session")
def integration_settings() -> IntegrationSettings:
    """Provide test-specific settings."""
    return IntegrationSettings()


@pytest.fixture(scope="session")
async def test_engine(
    integration_settings: IntegrationSettings,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine with NullPool for test isolation."""
    engine = create_async_engine(
        str(integration_settings.async_database_url),
        poolclass=NullPool,
        future=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_connection(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncConnection, None]:
    """Provide transactional connection for test isolation."""
    async with test_engine.connect() as connection:
        await connection.begin()
        await connection.run_sync(SQLModel.metadata.create_all)
        yield connection
        await connection.rollback()


@pytest.fixture
async def test_session(
    test_connection: AsyncConnection,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide database session with automatic rollback."""
    async with AsyncSession(bind=test_connection, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def override_get_session(test_session: AsyncSession) -> None:
    """Override get_session dependency with test session."""

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_session] = _get_test_session


@pytest.fixture(scope="session")
def normal_user_data() -> dict[str, Any]:
    """Provide normal user creation data."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": SecretStr("testpass123"),
        "first_name": "Test",
        "last_name": "User",
        "role": UserRole.USER,
    }


@pytest.fixture(scope="session")
def admin_user_data() -> dict[str, Any]:
    """Provide admin user creation data."""
    return {
        "username": "testadmin",
        "email": "testadmin@example.com",
        "password": SecretStr("testpass123"),
        "first_name": "Test",
        "last_name": "Admin",
        "role": UserRole.ADMIN,
    }


@pytest.fixture
async def ensure_test_users(
    test_session: AsyncSession,
    normal_user_data: dict[str, Any],
    admin_user_data: dict[str, Any],
) -> tuple[User, User]:
    """Provide normal and admin test users.

    The admin user is created by app/db/initialize.py during test setup
    and retrieved here. The normal user is created for testing purposes.
    """
    repository = get_user_repository(test_session)
    user_service = UserService(repository, password_service)

    normal_user = await repository.get_by_mail(normal_user_data["email"])
    if not normal_user:
        normal_user_create = UserCreate(**normal_user_data)
        normal_user = await user_service.create_user(normal_user_create)
        await test_session.commit()
        await test_session.refresh(normal_user)

    admin_user = await repository.get_by_mail(admin_user_data["email"])
    if not admin_user:
        msg = (
            f"Admin user {admin_user_data['email']} not found. "
            "Ensure app/db/initialize.py runs before tests."
        )
        raise RuntimeError(msg)

    return normal_user, admin_user


@pytest.fixture
def normal_user_credentials(normal_user_data: dict[str, Any]) -> dict[str, str]:
    """Provide normal user credentials for authentication."""
    return {
        "username": normal_user_data["username"],
        "password": normal_user_data["password"].get_secret_value(),
    }


@pytest.fixture
def admin_user_credentials(admin_user_data: dict[str, Any]) -> dict[str, str]:
    """Provide admin user credentials for authentication."""
    return {
        "username": admin_user_data["username"],
        "password": admin_user_data["password"].get_secret_value(),
    }


@pytest.fixture
async def unauthorized_client(
    integration_settings: IntegrationSettings,
    override_get_session: None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide httpx async client without authentication."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=f"http://testserver{integration_settings.api_path}",
    ) as client:
        yield client


@pytest.fixture
def create_authenticated_client(
    unauthorized_client: httpx.AsyncClient,
    integration_settings: IntegrationSettings,
    ensure_test_users: tuple[User, User],
) -> AuthenticatedClientFactory:
    """Factory fixture for creating authenticated clients with specified credentials."""

    async def _create(
        credentials: dict[str, str],
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        login_response = await unauthorized_client.post(
            "/auth/jwt/login",
            data=credentials,
        )
        assert login_response.status_code == 200

        token_data = TokenResponse(**login_response.json())

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=f"http://testserver{integration_settings.api_path}",
            headers={"Authorization": f"Bearer {token_data.access_token}"},
        ) as client:
            yield client

    return _create


@pytest.fixture
async def authenticated_client(
    create_authenticated_client: AuthenticatedClientFactory,
    normal_user_credentials: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide httpx async client authenticated as normal user via JWT."""
    async for client in create_authenticated_client(normal_user_credentials):
        yield client


@pytest.fixture
async def admin_client(
    create_authenticated_client: AuthenticatedClientFactory,
    admin_user_credentials: dict[str, str],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide httpx async client authenticated as admin user via JWT."""
    async for client in create_authenticated_client(admin_user_credentials):
        yield client


@pytest.fixture
async def mock_authenticated_client(
    integration_settings: IntegrationSettings,
    override_get_session: None,
    ensure_test_users: tuple[User, User],
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide httpx async client with mocked authentication."""
    normal_user, _ = ensure_test_users

    async def _mock_require_user() -> User:
        return normal_user

    auth_service = get_auth_service()
    app.dependency_overrides[auth_service.require_user] = _mock_require_user

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url=f"http://testserver{integration_settings.api_path}",
    ) as client:
        yield client

    app.dependency_overrides.pop(auth_service.require_user, None)
