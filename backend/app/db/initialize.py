import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.dependencies import password_service
from app.domains.users.exceptions import UserNotFoundError
from app.domains.users.models import UserRole
from app.domains.users.repositories import UserRepository
from app.domains.users.schemas import UserCreate
from app.domains.users.services import UserService


async def init_db() -> None:
    """Initialize the database with required system data.

    Creates a database session and ensures that a super user account exists.
    This function is typically called during application startup or via the
    CLI to bootstrap a fresh database with administrative access.

    The super user credentials are loaded from application settings and
    should be configured via environment variables (SUPER_USER__NAME,
    SUPER_USER__PASSWORD, SUPER_USER__EMAIL).
    """
    async for session in get_session():
        await ensure_super_user(session)


async def ensure_super_user(session: AsyncSession) -> None:
    """Ensure a super user account exists in the database.

    Checks if a super user with the configured username already exists.
    If not found, creates a new super user with admin role using credentials
    from application settings. This guarantees administrative access even on
    a freshly initialized database.

    The function is idempotent - it can be safely called multiple times
    without creating duplicate accounts.

    Args:
        session: Active database session for executing queries.

    Raises:
        ValidationError: If super user credentials from settings are invalid.
        DatabaseError: If database operations fail during user creation.
    """
    service = UserService(UserRepository(session), password_service)
    settings = get_settings()
    try:
        await service.get_by_name(settings.super_user.name)
    except UserNotFoundError:
        user_data = UserCreate.model_construct(
            username=settings.super_user.name,
            password=settings.super_user.password,
            email=settings.super_user.email,
            role=UserRole.ADMIN,
        )
        await service.create_user(user_data)


def main() -> None:
    """Initialize the database."""
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
