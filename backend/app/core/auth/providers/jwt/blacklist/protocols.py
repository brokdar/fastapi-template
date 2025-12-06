"""Protocol definition for token blacklist stores."""

from typing import Protocol


class TokenBlacklistStore(Protocol):
    """Protocol for token blacklist storage backends.

    Implementations must provide async methods for adding tokens to the
    blacklist and checking if a token is blacklisted. The store should
    handle automatic expiration of entries based on the provided TTL.

    Example:
        ```python
        store: TokenBlacklistStore = InMemoryTokenBlacklistStore()
        await store.add("token-jti-123", expires_in_seconds=900)
        is_blocked = await store.is_blacklisted("token-jti-123")
        ```
    """

    async def add(self, token_jti: str, expires_in_seconds: int) -> None:
        """Add a token JTI to the blacklist.

        Args:
            token_jti: The JWT ID (jti claim) to blacklist.
            expires_in_seconds: TTL for the blacklist entry (should match token expiry).
        """
        ...

    async def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token JTI is blacklisted.

        Args:
            token_jti: The JWT ID to check.

        Returns:
            True if the token is blacklisted, False otherwise.
        """
        ...
