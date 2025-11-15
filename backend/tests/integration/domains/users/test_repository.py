"""Integration tests for UserRepository custom methods."""

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from app.dependencies import get_user_repository
from app.domains.users.models import User, UserRole


class TestUserRepositoryGetByName:
    """Test suite for UserRepository.get_by_name() method."""

    @pytest.mark.asyncio
    async def test_retrieves_user_by_username_successfully(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test retrieving user by username returns correct user."""
        repository = get_user_repository(test_session)

        test_user = User(
            username="repotest1",
            email="repotest1@example.com",
            hashed_password="hashed_password_123",
            role=UserRole.USER,
        )
        created_user = await repository.create(test_user)
        await test_session.flush()

        result = await repository.get_by_name("repotest1")

        assert result is not None
        assert result.id == created_user.id
        assert result.username == "repotest1"
        assert result.email == "repotest1@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_username_not_found(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test get_by_name returns None when username does not exist."""
        repository = get_user_repository(test_session)

        result = await repository.get_by_name("nonexistent_user")

        assert result is None

    @pytest.mark.asyncio
    async def test_retrieves_correct_user_among_multiple(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test get_by_name retrieves correct user when multiple users exist."""
        repository = get_user_repository(test_session)

        user1 = User(
            username="repotest2",
            email="repotest2@example.com",
            hashed_password="hashed_password_123",
            role=UserRole.USER,
        )
        user2 = User(
            username="repotest3",
            email="repotest3@example.com",
            hashed_password="hashed_password_456",
            role=UserRole.ADMIN,
        )

        created_user1 = await repository.create(user1)
        created_user2 = await repository.create(user2)
        await test_session.flush()

        result1 = await repository.get_by_name("repotest2")
        result2 = await repository.get_by_name("repotest3")

        assert result1 is not None
        assert result1.id == created_user1.id
        assert result1.username == "repotest2"
        assert result1.email == "repotest2@example.com"

        assert result2 is not None
        assert result2.id == created_user2.id
        assert result2.username == "repotest3"
        assert result2.email == "repotest3@example.com"


class TestUserRepositoryGetByMail:
    """Test suite for UserRepository.get_by_mail() method."""

    @pytest.mark.asyncio
    async def test_retrieves_user_by_email_successfully(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test retrieving user by email returns correct user."""
        repository = get_user_repository(test_session)

        test_user = User(
            username="repotest4",
            email="repotest4@example.com",
            hashed_password="hashed_password_123",
            role=UserRole.USER,
        )
        created_user = await repository.create(test_user)
        await test_session.flush()

        result = await repository.get_by_mail("repotest4@example.com")

        assert result is not None
        assert result.id == created_user.id
        assert result.username == "repotest4"
        assert result.email == "repotest4@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_email_not_found(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test get_by_mail returns None when email does not exist."""
        repository = get_user_repository(test_session)

        result = await repository.get_by_mail("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_retrieves_correct_user_among_multiple(
        self,
        test_session: AsyncSession,
    ) -> None:
        """Test get_by_mail retrieves correct user when multiple users exist."""
        repository = get_user_repository(test_session)

        user1 = User(
            username="repotest5",
            email="repotest5@example.com",
            hashed_password="hashed_password_123",
            role=UserRole.USER,
        )
        user2 = User(
            username="repotest6",
            email="repotest6@example.com",
            hashed_password="hashed_password_456",
            role=UserRole.ADMIN,
        )

        created_user1 = await repository.create(user1)
        created_user2 = await repository.create(user2)
        await test_session.flush()

        result1 = await repository.get_by_mail("repotest5@example.com")
        result2 = await repository.get_by_mail("repotest6@example.com")

        assert result1 is not None
        assert result1.id == created_user1.id
        assert result1.username == "repotest5"
        assert result1.email == "repotest5@example.com"

        assert result2 is not None
        assert result2.id == created_user2.id
        assert result2.username == "repotest6"
        assert result2.email == "repotest6@example.com"
