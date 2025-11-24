"""API key hashing utilities.

This module provides secure API key generation, hashing, and verification
using bcrypt. Keys are generated with a 'sk_' prefix and 64 hex characters
(256 bits of entropy).
"""

import secrets
from typing import Protocol

import bcrypt


class APIKeyHasher(Protocol):
    """Protocol defining the interface for API key hashing operations.

    Implementations must provide methods for generating, hashing, verifying,
    and extracting prefixes from API keys.
    """

    def generate_key(self) -> tuple[str, str]:
        """Generate a new API key.

        Returns:
            tuple[str, str]: (plaintext_key, key_hash)
        """
        ...

    def hash_key(self, key: str) -> str:
        """Hash an API key.

        Args:
            key: The plaintext API key to hash.

        Returns:
            str: The hashed key.
        """
        ...

    def verify_key(self, plain_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash.

        Args:
            plain_key: The plaintext API key to verify.
            hashed_key: The hashed key to verify against.

        Returns:
            bool: True if the key matches, False otherwise.
        """
        ...

    def extract_prefix(self, key: str) -> str:
        """Extract the prefix from an API key for database lookup.

        Args:
            key: The full API key.

        Returns:
            str: The prefix portion of the key.
        """
        ...


class BCryptAPIKeyService(APIKeyHasher):
    """BCrypt-based API key service implementation.

    Provides secure API key generation, hashing, and verification using bcrypt.
    Keys are generated with a 'sk_' prefix and 64 hex characters (256 bits of entropy).

    Attributes:
        PREFIX: The prefix added to all generated API keys ('sk_').
        PREFIX_LENGTH: Number of characters used for key prefix lookup (12).
        BCRYPT_ROUNDS: Work factor for bcrypt hashing (12 by default).
    """

    PREFIX: str = "sk_"
    PREFIX_LENGTH: int = 12
    BCRYPT_ROUNDS: int = 12

    def generate_key(self) -> tuple[str, str]:
        """Generate a new API key with sk_ prefix.

        Returns:
            tuple[str, str]: (plaintext_key, key_hash)
        """
        random_part = secrets.token_hex(32)
        full_key = f"{self.PREFIX}{random_part}"
        key_hash = self.hash_key(full_key)
        return (full_key, key_hash)

    def hash_key(self, key: str) -> str:
        """Hash an API key using bcrypt.

        Args:
            key: The plaintext API key to hash.

        Returns:
            str: The bcrypt hashed key.
        """
        return bcrypt.hashpw(
            key.encode("utf-8"), bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        ).decode("utf-8")

    def verify_key(self, plain_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash using constant-time comparison.

        Args:
            plain_key: The plaintext API key to verify.
            hashed_key: The hashed key to verify against.

        Returns:
            bool: True if the key matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
        except ValueError:
            # Security: fail-closed on corrupted/tampered hash data to prevent bypass
            return False

    def extract_prefix(self, key: str) -> str:
        """Extract the first 12 characters of the key for database lookup.

        Args:
            key: The full API key.

        Returns:
            str: The first 12 characters of the key.

        Raises:
            ValueError: If key is shorter than PREFIX_LENGTH characters.
        """
        if len(key) < self.PREFIX_LENGTH:
            raise ValueError(
                f"API key must be at least {self.PREFIX_LENGTH} characters, got {len(key)}"
            )
        return key[: self.PREFIX_LENGTH]


default_api_key_service: APIKeyHasher = BCryptAPIKeyService()
