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
    """Initialize database with required initial data."""
    async for session in get_session():
        await ensure_super_user(session)


async def ensure_super_user(session: AsyncSession) -> None:
    """Ensure super user exists in database."""
    service = UserService(UserRepository(session), password_service)
    settings = get_settings()
    try:
        await service.get_by_name(settings.SUPER_USER.NAME)
    except UserNotFoundError:
        # Create super user if not found
        user_data = UserCreate.model_construct(
            username=settings.SUPER_USER.NAME,
            password=settings.SUPER_USER.PASSWORD,
            email=settings.SUPER_USER.EMAIL,
            role=UserRole.ADMIN,
        )
        await service.create_user(user_data)


def main() -> None:
    """Initialize the database."""
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
