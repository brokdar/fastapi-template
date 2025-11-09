"""Authentication service protocols for dependency injection.

This module defines protocol interfaces for authentication providers, following
the Interface Segregation Principle (ISP). Auth providers only depend on the
minimal interface they need, not the full user service implementation.
"""

from typing import Protocol
from uuid import UUID

from app.domains.users.models import User


class AuthenticationUserService[ID: (int, UUID)](Protocol):
    """Minimal user service interface for authentication operations.

    This protocol defines the user-related operations required by authentication
    providers. It follows the Interface Segregation Principle by exposing only
    the methods needed for authentication, not full user management operations.

    Any service implementing these methods can be used by auth providers,
    including UserService, test mocks, and alternative implementations.

    The protocol uses structural typing - no explicit inheritance required.
    UserService automatically satisfies this protocol because it implements
    all required methods with compatible signatures.

    Example:
        >>> # UserService automatically satisfies this protocol
        >>> user_service = UserService(repository, password_service)
        >>> provider = JWTAuthProvider(...)
        >>> user = await provider.authenticate(request, user_service)

    Methods:
        get_by_id: Retrieve user by ID (for token-based authentication).
        get_by_name: Retrieve user by username (for credential authentication).
        verify_password: Verify user password (for credential authentication).
    """

    async def get_by_id(self, user_id: ID) -> User:
        """Retrieve user by ID.

        Used by token-based authentication providers to lookup users
        after extracting user ID from tokens (JWT, session, etc.).

        Args:
            user_id: User identifier.

        Returns:
            User object.

        Raises:
            UserNotFoundError: If user with given ID doesn't exist.
        """
        ...

    async def get_by_name(self, username: str) -> User:
        """Retrieve user by username.

        Used by credential-based authentication providers for login
        operations where username/password is provided.

        Args:
            username: Username to lookup.

        Returns:
            User object.

        Raises:
            UserNotFoundError: If user with given username doesn't exist.
        """
        ...

    async def verify_password(self, user: User, password: str) -> bool:
        """Verify user password against stored hash.

        Used by credential-based authentication providers to validate
        passwords during login operations.

        Args:
            user: User object with hashed password.
            password: Plain text password to verify.

        Returns:
            True if password matches, False otherwise.
        """
        ...
