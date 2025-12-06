"""Factory for creating token blacklist store instances."""

from typing import TYPE_CHECKING

import structlog
from pydantic import RedisDsn

from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore
from app.core.auth.providers.jwt.blacklist.protocols import TokenBlacklistStore

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = structlog.get_logger("auth.blacklist.factory")


class LazyRedisBlacklistStore(TokenBlacklistStore):
    """Redis blacklist store with lazy initialization.

    Defers Redis client acquisition until first use, allowing the store
    to be created before RedisClient.initialize() is called (e.g., during
    module import). Gets fresh Redis client on each operation to handle
    connection pool reinitializations (e.g., during tests).
    """

    def __init__(self, redis_url: RedisDsn, key_prefix: str = "jwt:blacklist:") -> None:
        """Initialize lazy store with Redis URL.

        Args:
            redis_url: Redis connection URL for logging.
            key_prefix: Key prefix for blacklist entries.
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._initialized = False

    def _get_redis(self) -> "Redis":
        """Get current Redis client from singleton."""
        from app.core.redis import RedisClient

        if not self._initialized:
            logger.info(
                "blacklist_store_initialized",
                backend="redis",
                url=_mask_redis_url(self._redis_url),
            )
            self._initialized = True

        return RedisClient.get()

    async def add(self, token_jti: str, expires_in_seconds: int) -> None:
        """Add token to blacklist."""
        key = f"{self._key_prefix}{token_jti}"
        await self._get_redis().setex(key, expires_in_seconds, "1")

    async def is_blacklisted(self, token_jti: str) -> bool:
        """Check if token is blacklisted."""
        key = f"{self._key_prefix}{token_jti}"
        result = await self._get_redis().exists(key)
        return bool(result)


def create_blacklist_store(redis_url: RedisDsn | None = None) -> TokenBlacklistStore:
    """Create appropriate blacklist store based on configuration.

    Creates a lazy Redis-based store when a Redis URL is provided, otherwise
    falls back to an in-memory store. The in-memory store is suitable
    for development and testing.

    The Redis store uses lazy initialization - it won't connect to Redis
    until the first add() or is_blacklisted() call. This allows the store
    to be created before RedisClient.initialize() runs in the lifespan.

    Args:
        redis_url: Redis connection URL (validated by Pydantic). If None, uses in-memory store.

    Returns:
        TokenBlacklistStore implementation (lazy Redis or in-memory).

    Example:
        ```python
        # Production with Redis (lazy - doesn't require Redis yet)
        store = create_blacklist_store(RedisDsn("redis://localhost:6379/0"))

        # Development with in-memory
        store = create_blacklist_store()
        ```
    """
    if redis_url:
        logger.info("blacklist_store_created", backend="redis", lazy=True)
        return LazyRedisBlacklistStore(redis_url)

    logger.info("blacklist_store_created", backend="memory")
    return InMemoryTokenBlacklistStore()


def _mask_redis_url(url: RedisDsn) -> str:
    """Mask sensitive parts of Redis URL for logging.

    Uses Pydantic's RedisDsn parsed components for clean URL reconstruction.

    Args:
        url: Pydantic-validated Redis connection URL.

    Returns:
        URL with password masked if present, unchanged if no password.
    """
    if not url.password:
        return str(url)

    auth = f"{url.username}:***" if url.username else ":***"
    port_part = f":{url.port}" if url.port else ""
    path_part = url.path or ""
    return f"{url.scheme}://{auth}@{url.host}{port_part}{path_part}"
