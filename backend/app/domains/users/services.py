"""User domain service layer.

This module contains the business logic for user management operations.
All business rules, validation, and orchestration logic is handled here.
"""

from uuid import UUID

import structlog

from app.core.security.password import PasswordHasher

from .exceptions import UserAlreadyExistsError, UserNotFoundError
from .mixins import IntIDMixin, UUIDIDMixin
from .models import User
from .repositories import UserRepository
from .schemas import UserCreate, UserUpdate


class UserService[ID: (int, UUID)]:
    """Service class for user business logic operations.

    This class defines the core business logic and an abstract parse_id
    method. Concrete implementations should compose this class with an
    ID parsing mixin (IntIDMixin or UUIDIDMixin) via multiple inheritance.

    The mixin must be listed BEFORE UserService in the inheritance order
    to ensure Python's Method Resolution Order (MRO) resolves parse_id
    to the mixin's implementation.

    Example:
        >>> from app.domains.users.mixins import IntIDMixin
        >>> class IntUserService(IntIDMixin, UserService[int]):
        ...     pass
        >>> service = IntUserService(repository, password_service)
        >>> user_id = service.parse_id("123")  # Returns 123 (int)
    """

    def __init__(
        self,
        user_repository: UserRepository[ID],
        password_service: PasswordHasher,
    ) -> None:
        """Initialize UserService with repository dependency.

        Args:
            user_repository: Repository for user data access operations
            password_service: Service for password hashing and verification
        """
        self._repository: UserRepository[ID] = user_repository
        self._password_service = password_service
        self.logger = structlog.get_logger("users")

    def parse_id(self, value: str) -> ID:
        """Parse string ID to typed ID (implemented by mixins).

        This method is abstract and must be implemented by composing
        UserService with an ID mixin (IntIDMixin or UUIDIDMixin) via
        multiple inheritance. The mixin implementation will be resolved
        via Python's Method Resolution Order (MRO).

        Args:
            value: String representation of user ID.

        Returns:
            Typed ID instance.

        Raises:
            InvalidUserIDError: If parsing fails (raised by mixin).
            NotImplementedError: If UserService is used without a mixin.
        """
        raise NotImplementedError(
            "UserService must be composed with an ID mixin "
            "(IntIDMixin or UUIDIDMixin) to provide parse_id implementation. "
            "Example: class IntUserService(IntIDMixin, UserService[int]): pass"
        )

    async def verify_password(self, user: User, password: str) -> bool:
        """Verify user password against stored hash.

        Args:
            user: User instance with hashed password.
            password: Plain text password to verify.

        Returns:
            True if password matches, False otherwise.
        """
        return self._password_service.verify_password(password, user.hashed_password)

    async def _validate_email_unique(
        self, email: str, exclude_user_id: ID | None = None
    ) -> None:
        """Validate that email is unique in the system.

        Args:
            email: Email address to validate
            exclude_user_id: User ID to exclude from uniqueness check (for updates)

        Raises:
            UserAlreadyExistsError: If email already exists for another user
        """
        existing_user = await self._repository.get_by_mail(email)
        if existing_user and existing_user.id != exclude_user_id:
            raise UserAlreadyExistsError(
                message=f"User with email {email} already exists",
                field="email",
                value=email,
            )

    async def _validate_username_unique(
        self, username: str, exclude_user_id: ID | None = None
    ) -> None:
        """Validate that username is unique in the system.

        Args:
            username: Username to validate
            exclude_user_id: User ID to exclude from uniqueness check (for updates)

        Raises:
            UserAlreadyExistsError: If username already exists for another user
        """
        existing_user = await self._repository.get_by_name(username)
        if existing_user and existing_user.id != exclude_user_id:
            raise UserAlreadyExistsError(
                message=f"User with username {username} already exists",
                field="username",
                value=username,
            )

    async def get_by_id(self, user_id: ID) -> User:
        """Retrieve a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            The user with the specified ID

        Raises:
            UserNotFoundError: If user with given ID doesn't exist
        """
        user = await self._repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(
                message=f"User with ID {user_id} not found", user_id=user_id
            )

        self.logger.info(
            "user_retrieved",
            user_id=user_id,
            username=user.username,
            operation="get_by_id",
        )

        return user

    async def get_by_name(self, username: str) -> User:
        """Retrieve a user by username.

        Args:
            username: The username of the user to retrieve

        Returns:
            The user with the specified username

        Raises:
            UserNotFoundError: If user with given username doesn't exist
        """
        user = await self._repository.get_by_name(username)
        if not user:
            raise UserNotFoundError(
                message=f"User with username '{username}' not found", user_id=username
            )

        self.logger.info(
            "user_retrieved",
            user_id=user.id,
            username=user.username,
            operation="get_by_name",
        )

        return user

    async def get_all(
        self,
        offset: int | None = None,
        limit: int | None = None,
    ) -> tuple[list[User], int]:
        """Retrieve paginated list of users with total count.

        Args:
            offset: Number of items to skip. If None, returns all users.
            limit: Maximum number of items to return. If None, returns all users.

        Returns:
            Tuple of (users list, total count)
        """
        if offset is not None and limit is not None:
            users = await self._repository.get_paginated(offset=offset, limit=limit)
            total = await self._repository.count()
        else:
            users = await self._repository.get_all()
            total = len(users)

        self.logger.info(
            "users_retrieved",
            count=len(users),
            total=total,
            offset=offset,
            limit=limit,
            operation="get_all",
        )

        return users, total

    async def count(self) -> int:
        """Get total count of users in the system.

        Returns:
            Total number of users
        """
        total = await self._repository.count()

        self.logger.info("users_counted", total=total, operation="count")

        return total

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user.

        Args:
            user_data: User creation data

        Returns:
            The created user

        Raises:
            UserAlreadyExistsError: If user with same email or username exists
        """
        await self._validate_email_unique(user_data.email)
        await self._validate_username_unique(user_data.username)

        hashed_password = self._password_service.hash_password(
            user_data.password.get_secret_value()
        )
        user = User(
            **user_data.model_dump(exclude={"password"}),
            hashed_password=hashed_password,
        )

        created_user = await self._repository.create(user)

        self.logger.info(
            "user_created",
            user_id=created_user.id,
            username=created_user.username,
            email=created_user.email,
            role=created_user.role,
            operation="create",
        )

        return created_user

    async def update_user(self, user_id: ID, user_update: UserUpdate) -> User:
        """Update an existing user.

        Args:
            user_id: ID of the user to update
            user_update: User update data

        Returns:
            The updated user

        Raises:
            UserNotFoundError: If user with given ID doesn't exist
            UserAlreadyExistsError: If update would create duplicate email/username
        """
        existing_user = await self._repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(
                message=f"User with ID {user_id} not found", user_id=user_id
            )

        update_data = user_update.model_dump(exclude_unset=True)

        if "email" in update_data:
            await self._validate_email_unique(
                update_data["email"], exclude_user_id=user_id
            )

        if "username" in update_data:
            await self._validate_username_unique(
                update_data["username"], exclude_user_id=user_id
            )

        for field, value in update_data.items():
            setattr(existing_user, field, value)

        updated_user = await self._repository.update(existing_user)
        self.logger.info(
            "user_updated",
            user_id=user_id,
            username=updated_user.username,
            updated_fields=list(update_data.keys()),
            operation="update",
        )

        return updated_user

    async def delete_user(self, user_id: ID) -> None:
        """Delete a user.

        Args:
            user_id: ID of the user to delete

        Raises:
            UserNotFoundError: If user with given ID doesn't exist
        """
        existing_user = await self._repository.get_by_id(user_id)
        if not existing_user:
            raise UserNotFoundError(
                message=f"User with ID {user_id} not found", user_id=user_id
            )

        await self._repository.delete(user_id)

        self.logger.info(
            "user_deleted",
            user_id=user_id,
            username=existing_user.username,
            operation="delete",
        )


class IntUserService(IntIDMixin, UserService[int]):
    """UserService with integer ID parsing via IntIDMixin composition.

    MRO: IntUserService -> IntIDMixin -> UserService[int]
    The IntIDMixin.parse_id method overrides UserService.parse_id via
    Python's Method Resolution Order, providing integer ID parsing implementation.
    """

    pass


class UUIDUserService(UUIDIDMixin, UserService[UUID]):
    """UserService with UUID ID parsing via UUIDIDMixin composition.

    MRO: UUIDUserService -> UUIDIDMixin -> UserService[UUID]
    The UUIDIDMixin.parse_id method overrides UserService.parse_id via
    Python's Method Resolution Order, providing UUID ID parsing implementation.
    """

    pass
