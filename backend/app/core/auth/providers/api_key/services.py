"""API Key service layer.

This module contains the business logic for API key management operations.
All business rules, validation, and orchestration logic is handled here.
"""

from datetime import UTC, datetime, timedelta

import structlog

from app.core.base.repositories.exceptions import RepositoryError
from app.core.security.hasher import APIKeyHasher

from .exceptions import (
    APIKeyExpiredError,
    APIKeyLimitExceededError,
    APIKeyNotFoundError,
    InvalidAPIKeyError,
)
from .models import APIKey
from .repositories import APIKeyRepository


class APIKeyService:
    """Service class for API key business logic operations.

    This class handles the core business logic for API key management
    including creation, deletion, listing, and validation.
    """

    def __init__(
        self,
        repository: APIKeyRepository,
        hasher: APIKeyHasher,
        max_per_user: int = 5,
        default_expiration_days: int = 30,
    ) -> None:
        """Initialize APIKeyService with dependencies.

        Args:
            repository: Repository for API key data access operations
            hasher: Service for API key hashing and verification
            max_per_user: Maximum number of API keys allowed per user
            default_expiration_days: Default expiration period in days for new keys
        """
        self._repository = repository
        self._hasher = hasher
        self._max_per_user = max_per_user
        self._default_expiration_days = default_expiration_days
        self.logger: structlog.stdlib.BoundLogger = structlog.get_logger("auth.api_key")

    async def create_key(
        self,
        user_id: int,
        name: str,
        expires_in_days: int | None = None,
    ) -> tuple[str, APIKey]:
        """Create a new API key for a user.

        Args:
            user_id: ID of the user to create the key for
            name: Human-readable name for the API key
            expires_in_days: Number of days until key expires (uses default if None)

        Returns:
            Tuple of (plaintext_key, api_key_model). The plaintext key is only
            returned once and should be shown to the user immediately.

        Raises:
            APIKeyLimitExceededError: If user has reached maximum allowed keys
        """
        current_count = await self._repository.count_by_user(user_id)
        if current_count >= self._max_per_user:
            raise APIKeyLimitExceededError(
                max_allowed=self._max_per_user,
                current_count=current_count,
            )

        plaintext_key, key_hash = self._hasher.generate_key()
        key_prefix = self._hasher.extract_prefix(plaintext_key)

        expiration_days = (
            expires_in_days
            if expires_in_days is not None
            else self._default_expiration_days
        )
        expires_at = datetime.now(UTC) + timedelta(days=expiration_days)

        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            expires_at=expires_at,
        )

        created_key = await self._repository.create(api_key)

        self.logger.info(
            "api_key_created",
            user_id=user_id,
            key_id=created_key.id,
            key_name=name,
        )

        return (plaintext_key, created_key)

    async def delete_key(self, key_id: int, user_id: int) -> None:
        """Delete an API key owned by a specific user.

        Args:
            key_id: ID of the API key to delete
            user_id: ID of the user who owns the key

        Raises:
            APIKeyNotFoundError: If key doesn't exist or doesn't belong to user
        """
        api_key = await self._repository.get_by_id(key_id)
        if api_key is None or api_key.user_id != user_id:
            raise APIKeyNotFoundError(key_id=key_id)

        await self._repository.delete(key_id)

        self.logger.info(
            "api_key_deleted",
            user_id=user_id,
            key_id=key_id,
            key_name=api_key.name,
        )

    async def delete_key_admin(self, key_id: int, admin_id: int) -> None:
        """Delete any API key (admin operation).

        Args:
            key_id: ID of the API key to delete
            admin_id: ID of the admin performing the deletion

        Raises:
            APIKeyNotFoundError: If key doesn't exist
        """
        api_key = await self._repository.get_by_id(key_id)
        if api_key is None:
            raise APIKeyNotFoundError(key_id=key_id)

        owner_user_id = api_key.user_id
        await self._repository.delete(key_id)

        self.logger.info(
            "api_key_deleted_by_admin",
            admin_id=admin_id,
            key_id=key_id,
            owner_user_id=owner_user_id,
        )

    async def list_keys(self, user_id: int) -> list[APIKey]:
        """List API keys for a user.

        Args:
            user_id: ID of the user whose keys to list

        Returns:
            List of API keys belonging to the user
        """
        return await self._repository.get_by_user_id(user_id)

    async def validate_key(self, key: str) -> tuple[int, int]:
        """Validate an API key and return associated user/key IDs.

        Args:
            key: The plaintext API key to validate

        Returns:
            Tuple of (user_id, key_id) if validation succeeds

        Raises:
            InvalidAPIKeyError: If key format is invalid, not found, or hash mismatch
            APIKeyExpiredError: If key has expired
        """
        # Fast format check before database lookup to reject obviously invalid keys
        if not self._is_valid_key_format(key):
            self.logger.warning("api_key_validation_failed", reason="invalid_format")
            raise InvalidAPIKeyError(message="Invalid API key format")

        # Note: No timing attack protection for prefix lookup. Prefixes are public
        # identifiers (returned in API responses), and the 256-bit secret prevents brute-force.
        prefix = self._hasher.extract_prefix(key)
        api_key = await self._repository.get_by_prefix(prefix)

        if api_key is None:
            self.logger.warning(
                "api_key_validation_failed", reason="key_not_found", prefix=prefix
            )
            raise InvalidAPIKeyError(message="API key not found")

        if api_key.expires_at is not None and api_key.expires_at < datetime.now(UTC):
            raise APIKeyExpiredError(key_id=api_key.id)

        if not self._hasher.verify_key(key, api_key.key_hash):
            self.logger.warning(
                "api_key_validation_failed",
                reason="hash_mismatch",
                key_id=api_key.id,
            )
            raise InvalidAPIKeyError(message="API key verification failed")

        if api_key.id is None:
            raise InvalidAPIKeyError("API key from database is missing ID")

        await self._update_last_used_safely(api_key.id)

        self.logger.info(
            "api_key_validated",
            user_id=api_key.user_id,
            key_id=api_key.id,
        )

        return (api_key.user_id, api_key.id)

    def _is_valid_key_format(self, key: str) -> bool:
        """Validate API key format.

        Expected format: sk_ prefix + 64 hex characters = 67 total characters.

        Args:
            key: The API key to validate.

        Returns:
            True if format is valid, False otherwise.
        """
        expected_length: int = 67
        expected_prefix: str = "sk_"

        if not key or len(key) != expected_length:
            return False
        if not key.startswith(expected_prefix):
            return False
        try:
            int(key[3:], 16)
            return True
        except ValueError:
            return False

    async def _update_last_used_safely(self, key_id: int) -> None:
        """Update last_used_at timestamp without failing authentication.

        This is a best-effort operation. Database failures are logged but not
        propagated, as tracking usage is secondary to authentication success.

        Args:
            key_id: ID of the API key to update.
        """
        try:
            await self._repository.update_last_used(key_id)
        except RepositoryError as e:
            self.logger.warning(
                "api_key_last_used_update_failed",
                key_id=key_id,
                error=str(e),
                error_type=type(e).__name__,
            )
