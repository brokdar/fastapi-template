"""User domain service layer.

This module contains the business logic for user management operations.
All business rules, validation, and orchestration logic is handled here.
"""

import structlog

from app.core.security.password import PasswordHasher

from .exceptions import UserAlreadyExistsError, UserNotFoundError
from .models import User, UserID, parse_user_id
from .repositories import UserRepository
from .schemas import UserCreate, UserUpdate


class UserService:
    """Service class for user business logic operations.

    This class handles core business logic for user management. Uses UserID
    type alias from models.py for ID type configuration.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordHasher,
    ) -> None:
        """Initialize UserService with repository dependency.

        Args:
            user_repository: Repository for user data access operations
            password_service: Service for password hashing and verification
        """
        self._repository: UserRepository = user_repository
        self._password_service = password_service
        self.logger = structlog.get_logger("users")

    def parse_id(self, value: str) -> UserID:
        """Parse string ID to UserID type.

        Args:
            value: String representation of user ID.

        Returns:
            Parsed UserID.

        Raises:
            ValueError: If parsing fails.
        """
        return parse_user_id(value)

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
        self, email: str, exclude_user_id: UserID | None = None
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
        self, username: str, exclude_user_id: UserID | None = None
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

    async def get_by_id(self, user_id: UserID) -> User:
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

    async def update_user(self, user_id: UserID, user_update: UserUpdate) -> User:
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

    async def delete_user(self, user_id: UserID) -> None:
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
