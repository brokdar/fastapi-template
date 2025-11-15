"""Test suite for UserService business logic."""

from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.domains.users.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.domains.users.mixins import IntIDMixin, UUIDIDMixin
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserUpdate
from app.domains.users.services import IntUserService, UserService


class TestUserServiceGetById:
    """Test suite for UserService.get_by_id method."""

    @pytest.mark.asyncio
    async def test_returns_user_when_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test successful user retrieval by ID."""
        mock_repository.get_by_id.return_value = regular_user

        result = await user_service.get_by_id(1)

        assert result == regular_user
        mock_repository.get_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_user_not_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test UserNotFoundError when user doesn't exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            await user_service.get_by_id(999)

        mock_repository.get_by_id.assert_called_once_with(999)


class TestUserServiceGetByName:
    """Test suite for UserService.get_by_name method."""

    @pytest.mark.asyncio
    async def test_returns_user_when_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test successful user retrieval by username."""
        mock_repository.get_by_name.return_value = regular_user

        result = await user_service.get_by_name("sampleuser")

        assert result == regular_user
        mock_repository.get_by_name.assert_called_once_with("sampleuser")

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_user_not_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test UserNotFoundError when username doesn't exist."""
        mock_repository.get_by_name.return_value = None

        with pytest.raises(
            UserNotFoundError, match="User with username 'nonexistent' not found"
        ):
            await user_service.get_by_name("nonexistent")

        mock_repository.get_by_name.assert_called_once_with("nonexistent")


class TestUserServiceGetAll:
    """Test suite for UserService.get_all method."""

    @pytest.mark.asyncio
    async def test_returns_paginated_users(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test successful paginated user retrieval."""
        expected_users = [regular_user]
        mock_repository.get_paginated.return_value = expected_users
        mock_repository.count.return_value = 1

        users, total = await user_service.get_all(offset=0, limit=10)

        assert users == expected_users
        assert total == 1
        mock_repository.get_paginated.assert_called_once_with(offset=0, limit=10)
        mock_repository.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_default_pagination_parameters(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test default pagination parameters when no parameters provided."""
        mock_repository.get_all.return_value = []

        users, total = await user_service.get_all()

        assert users == []
        assert total == 0
        mock_repository.get_all.assert_called_once()
        mock_repository.get_paginated.assert_not_called()


class TestUserServiceCount:
    """Test suite for UserService.count method."""

    @pytest.mark.asyncio
    async def test_returns_total_user_count(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test total user count retrieval."""
        expected_count = 42
        mock_repository.count.return_value = expected_count

        result = await user_service.count()

        assert result == expected_count
        mock_repository.count.assert_called_once()


class TestUserServiceCreateUser:
    """Test suite for UserService.create_user method."""

    @pytest.mark.asyncio
    async def test_creates_user_when_no_conflicts(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        user_create_data: UserCreate,
        regular_user: User,
    ) -> None:
        """Test successful user creation."""
        mock_repository.get_by_mail.return_value = None
        mock_repository.get_by_name.return_value = None
        mock_repository.create.return_value = regular_user

        result = await user_service.create_user(user_create_data)

        assert result == regular_user
        mock_repository.get_by_mail.assert_called_once_with(user_create_data.email)
        mock_repository.get_by_name.assert_called_once_with(user_create_data.username)
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_already_exists_error_when_email_conflict(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        user_create_data: UserCreate,
        regular_user: User,
    ) -> None:
        """Test UserAlreadyExistsError when email already exists."""
        mock_repository.get_by_mail.return_value = regular_user

        with pytest.raises(
            UserAlreadyExistsError, match="User with email .* already exists"
        ):
            await user_service.create_user(user_create_data)

        mock_repository.get_by_mail.assert_called_once_with(user_create_data.email)
        assert not mock_repository.create.called

    @pytest.mark.asyncio
    async def test_raises_already_exists_error_when_username_conflict(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        user_create_data: UserCreate,
        regular_user: User,
    ) -> None:
        """Test UserAlreadyExistsError when username already exists."""
        mock_repository.get_by_mail.return_value = None
        mock_repository.get_by_name.return_value = regular_user

        with pytest.raises(
            UserAlreadyExistsError, match="User with username .* already exists"
        ):
            await user_service.create_user(user_create_data)

        mock_repository.get_by_mail.assert_called_once_with(user_create_data.email)
        mock_repository.get_by_name.assert_called_once_with(user_create_data.username)
        assert not mock_repository.create.called


class TestUserServiceUpdateUser:
    """Test suite for UserService.update_user method."""

    @pytest.mark.asyncio
    async def test_updates_user_when_exists_and_no_conflicts(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test successful user update."""
        user_update = UserUpdate.model_validate(
            {"first_name": "Updated", "is_active": False}
        )
        updated_user = User(
            **{**regular_user.model_dump(), "first_name": "Updated", "is_active": False}
        )

        mock_repository.get_by_id.return_value = regular_user
        mock_repository.update.return_value = updated_user

        result = await user_service.update_user(1, user_update)

        assert result == updated_user
        mock_repository.get_by_id.assert_called_once_with(1)
        mock_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_user_not_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test UserNotFoundError when updating non-existent user."""
        user_update = UserUpdate.model_validate({"first_name": "Updated"})
        mock_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            await user_service.update_user(999, user_update)

        mock_repository.get_by_id.assert_called_once_with(999)
        assert not mock_repository.update.called

    @pytest.mark.asyncio
    async def test_raises_already_exists_error_on_email_conflict(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test UserAlreadyExistsError when updating to existing email."""
        user_update = UserUpdate.model_validate({"email": "conflict@example.com"})
        conflicting_user = User(
            **{**regular_user.model_dump(), "id": 2, "email": "conflict@example.com"}
        )

        mock_repository.get_by_id.return_value = regular_user
        mock_repository.get_by_mail.return_value = conflicting_user

        with pytest.raises(
            UserAlreadyExistsError, match="User with email .* already exists"
        ):
            await user_service.update_user(1, user_update)

        mock_repository.get_by_id.assert_called_once_with(1)
        mock_repository.get_by_mail.assert_called_once_with("conflict@example.com")
        assert not mock_repository.update.called

    @pytest.mark.asyncio
    async def test_allows_updating_to_same_email(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test updating user with same email doesn't raise conflict."""
        user_update = UserUpdate.model_validate(
            {"email": regular_user.email, "first_name": "Updated"}
        )

        mock_repository.get_by_id.return_value = regular_user
        mock_repository.get_by_mail.return_value = regular_user
        mock_repository.update.return_value = regular_user

        result = await user_service.update_user(1, user_update)

        assert result == regular_user
        mock_repository.update.assert_called_once()

    @pytest.mark.parametrize(
        ("update_data", "expected_calls"),
        [
            ({"first_name": "Updated"}, 0),  # No email/username checks
            ({"email": "new@example.com"}, 1),  # Email check only
            ({"username": "newusername"}, 1),  # Username check only
            ({"email": "new@example.com", "username": "newusername"}, 2),  # Both checks
        ],
        ids=["no_unique_fields", "email_only", "username_only", "both_unique_fields"],
    )
    @pytest.mark.asyncio
    async def test_update_validation_calls_depend_on_fields(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
        update_data: dict[str, Any],
        expected_calls: int,
    ) -> None:
        """Test that validation calls depend on which fields are updated."""
        user_update = UserUpdate(**update_data)

        mock_repository.get_by_id.return_value = regular_user
        mock_repository.get_by_mail.return_value = None
        mock_repository.get_by_name.return_value = None
        mock_repository.update.return_value = regular_user

        await user_service.update_user(1, user_update)

        total_validation_calls = (
            mock_repository.get_by_mail.call_count
            + mock_repository.get_by_name.call_count
        )
        assert total_validation_calls == expected_calls


class TestUserServiceDeleteUser:
    """Test suite for UserService.delete_user method."""

    @pytest.mark.asyncio
    async def test_deletes_user_when_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
        regular_user: User,
    ) -> None:
        """Test successful user deletion."""
        mock_repository.get_by_id.return_value = regular_user
        mock_repository.delete.return_value = None

        await user_service.delete_user(1)

        mock_repository.get_by_id.assert_called_once_with(1)
        mock_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_raises_not_found_error_when_user_not_exists(
        self,
        user_service: UserService[int],
        mock_repository: AsyncMock,
    ) -> None:
        """Test UserNotFoundError when deleting non-existent user."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFoundError, match="User with ID 999 not found"):
            await user_service.delete_user(999)

        mock_repository.get_by_id.assert_called_once_with(999)
        assert not mock_repository.delete.called


class TestUserServiceParseId:
    """Test suite for UserService.parse_id method and mixin composition."""

    def test_raises_not_implemented_without_mixin(
        self, mock_repository: AsyncMock, mock_password_service: AsyncMock
    ) -> None:
        """Test that pure UserService without mixin raises NotImplementedError."""
        service = UserService(mock_repository, mock_password_service)

        with pytest.raises(
            NotImplementedError, match="must be composed with an ID mixin"
        ):
            service.parse_id("123")

    def test_int_user_service_parses_integer_ids(
        self, mock_repository: AsyncMock, mock_password_service: AsyncMock
    ) -> None:
        """Test IntUserService parses integer IDs via IntIDMixin."""
        service = IntUserService(mock_repository, mock_password_service)

        result = service.parse_id("123")

        assert result == 123
        assert isinstance(result, int)

    def test_uuid_user_service_parses_uuid_ids(
        self, mock_repository: AsyncMock, mock_password_service: AsyncMock
    ) -> None:
        """Test UUIDUserService parses UUID IDs via UUIDIDMixin."""

        class UUIDUserService(UUIDIDMixin, UserService[UUID]):
            pass

        service = UUIDUserService(mock_repository, mock_password_service)
        uuid_str = "123e4567-e89b-12d3-a456-426614174000"

        result = service.parse_id(uuid_str)

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_mixin_method_resolution_order(
        self, mock_repository: AsyncMock, mock_password_service: AsyncMock
    ) -> None:
        """Test that MRO resolves parse_id to mixin implementation."""

        class TestService(IntIDMixin, UserService[int]):
            pass

        service = TestService(mock_repository, mock_password_service)
        mro = TestService.__mro__

        assert mro[0] == TestService
        assert mro[1] == IntIDMixin
        assert mro[2] == UserService
        assert hasattr(service, "parse_id")
        assert service.parse_id("456") == 456
