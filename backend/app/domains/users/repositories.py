from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.base.repositories.base import BaseRepository
from app.core.base.repositories.exceptions import handle_repository_errors

from .models import User


class UserRepository(BaseRepository[User]):
    """Repository for user-specific database operations.

    Extends BaseRepository to provide CRUD operations and custom queries
    for User entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an asynchronous database session.

        Args:
            session: The active asynchronous session to interact with the database.
        """
        super().__init__(session, User)

    @handle_repository_errors()
    async def get_by_name(self, name: str) -> User | None:
        """Retrieve a user by their username.

        Args:
            name: The username to search for.

        Returns:
            The User object if found, otherwise None.
        """
        statement = select(User).where(User.username == name)
        result = await self._session.exec(statement)
        return result.first()

    @handle_repository_errors()
    async def get_by_mail(self, mail: str) -> User | None:
        """Retrieve a user by their email address.

        Args:
            mail: The email address to search for.

        Returns:
            The User object if found, otherwise None.
        """
        statement = select(User).where(User.email == mail)
        result = await self._session.exec(statement)
        return result.first()
