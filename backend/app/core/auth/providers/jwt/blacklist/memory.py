"""In-memory token blacklist store implementation."""

import time

import structlog

logger = structlog.get_logger("auth.blacklist.memory")


class InMemoryTokenBlacklistStore:
    """In-memory token blacklist with lazy expiration cleanup.

    Stores blacklisted token JTIs in a dictionary with their expiration timestamps.
    Expired entries are cleaned up lazily when checking blacklist status or when
    the store exceeds a size threshold.

    Suitable for development, testing, and single-instance deployments.
    Not recommended for production multi-process deployments as each process
    maintains its own independent blacklist.
    """

    def __init__(self, cleanup_threshold: int = 1000) -> None:
        """Initialize the in-memory blacklist store.

        Args:
            cleanup_threshold: Number of entries that triggers cleanup.
        """
        self._blacklist: dict[str, float] = {}
        self._cleanup_threshold = cleanup_threshold

    async def add(self, token_jti: str, expires_in_seconds: int) -> None:
        """Add a token JTI to the blacklist with expiration.

        Args:
            token_jti: The JWT ID to blacklist.
            expires_in_seconds: Time until the entry expires.
        """
        expiry = time.time() + expires_in_seconds
        self._blacklist[token_jti] = expiry
        logger.debug(
            "token_blacklisted",
            jti=token_jti,
            expires_in=expires_in_seconds,
            store="memory",
        )

        if len(self._blacklist) > self._cleanup_threshold:
            self._cleanup_expired()

    async def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token JTI is blacklisted.

        Performs lazy cleanup of the checked entry if it has expired.

        Args:
            token_jti: The JWT ID to check.

        Returns:
            True if blacklisted and not expired, False otherwise.
        """
        expiry = self._blacklist.get(token_jti)
        if expiry is None:
            return False

        if time.time() > expiry:
            del self._blacklist[token_jti]
            return False

        return True

    def _cleanup_expired(self) -> None:
        """Remove expired entries from the blacklist."""
        now = time.time()
        expired_keys = [k for k, v in self._blacklist.items() if now > v]
        for key in expired_keys:
            del self._blacklist[key]

        if expired_keys:
            logger.debug(
                "blacklist_cleanup",
                removed_count=len(expired_keys),
                remaining_count=len(self._blacklist),
            )
