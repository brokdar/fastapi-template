"""Test suite for UserRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.domains.users.models import User
from app.domains.users.repositories import UserRepository


@pytest.fixture
def user_repository(mock_session: AsyncMock) -> UserRepository:
    """Return a UserRepository instance with a mocked session."""
    return UserRepository(mock_session)


@pytest.fixture
def mock_db_result() -> MagicMock:
    """Provide a mocked database result object."""
    mock = MagicMock()
    mock.first.return_value = None
    return mock


@pytest.fixture
def mock_db_result_with_user(regular_user: User) -> MagicMock:
    """Provide a mocked database result object with a user."""
    mock = MagicMock()
    mock.first.return_value = regular_user
    return mock


class TestUserRepositoryGetByName:
    """Test suite for UserRepository.get_by_name method."""

    @pytest.mark.asyncio
    async def test_retrieves_user_by_name_when_exists(
        self,
        user_repository: UserRepository,
        regular_user: User,
        mock_db_result_with_user: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test successful user retrieval by username."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result_with_user
        )

        result = await user_repository.get_by_name("testuser")

        assert result is regular_user
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_user_name_not_found(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test None return for non-existent username."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        result = await user_repository.get_by_name("nonexistent")

        assert result is None
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_correct_select_statement_for_name_query(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that correct select statement is generated for username query."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        await user_repository.get_by_name("testuser")

        call_args = mock_exec.call_args[0][0]
        statement_str = str(call_args)
        assert "SELECT" in statement_str
        assert '"user".username' in statement_str

    @pytest.mark.parametrize(
        "search_value",
        ["", "   "],
        ids=["empty_username", "whitespace_username"],
    )
    @pytest.mark.asyncio
    async def test_handles_empty_search_values(
        self,
        user_repository: UserRepository,
        search_value: str,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test handling of empty and whitespace search values."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        result = await user_repository.get_by_name(search_value)

        assert result is None
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_session_exec_once(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that session.exec is called exactly once."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        await user_repository.get_by_name("valid_username")

        mock_exec.assert_called_once()


class TestUserRepositoryGetByMail:
    """Test suite for UserRepository.get_by_mail method."""

    @pytest.mark.asyncio
    async def test_retrieves_user_by_email_when_exists(
        self,
        user_repository: UserRepository,
        regular_user: User,
        mock_db_result_with_user: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test successful user retrieval by email."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result_with_user
        )

        result = await user_repository.get_by_mail("test@example.com")

        assert result is regular_user
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_user_email_not_found(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test None return for non-existent email."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        result = await user_repository.get_by_mail("nonexistent@example.com")

        assert result is None
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_generates_correct_select_statement_for_email_query(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that correct select statement is generated for email query."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        await user_repository.get_by_mail("test@example.com")

        call_args = mock_exec.call_args[0][0]
        statement_str = str(call_args)
        assert "SELECT" in statement_str
        assert '"user".email' in statement_str

    @pytest.mark.parametrize(
        "search_value",
        ["", "   "],
        ids=["empty_email", "whitespace_email"],
    )
    @pytest.mark.asyncio
    async def test_handles_empty_search_values(
        self,
        user_repository: UserRepository,
        search_value: str,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test handling of empty and whitespace search values."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        result = await user_repository.get_by_mail(search_value)

        assert result is None
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_session_exec_once(
        self,
        user_repository: UserRepository,
        mock_db_result: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that session.exec is called exactly once."""
        mock_exec = mocker.patch.object(
            user_repository._session, "exec", return_value=mock_db_result
        )

        await user_repository.get_by_mail("valid@email.com")

        mock_exec.assert_called_once()
