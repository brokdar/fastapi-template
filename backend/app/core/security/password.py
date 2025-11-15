from typing import Protocol

import bcrypt


class PasswordHasher(Protocol):
    """Protocol for password hashing operations."""

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify if a plain password matches a hashed password.

        Args:
            plain_password (str): The plain text password to verify
            hashed_password (str): The hashed password to compare against

        Returns:
            bool: True if the passwords match, False otherwise
        """

    def hash_password(self, password: str) -> str:
        """Hash a plain text password.

        Args:
            password (str): The plain text password to hash

        Returns:
            str: The hashed password string
        """


class BCryptPasswordService(PasswordHasher):
    """BCrypt implementation of password hashing service."""

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify if a plain password matches a BCrypt hashed password.

        Args:
            plain_password (str): The plain text password to verify
            hashed_password (str): The BCrypt hashed password to compare against

        Returns:
            bool: True if the passwords match, False otherwise
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    def hash_password(self, password: str) -> str:
        """Hash a plain text password using BCrypt.

        Args:
            password (str): The plain text password to hash

        Returns:
            str: The BCrypt hashed password string
        """
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Default password service instance
default_password_service: PasswordHasher = BCryptPasswordService()
