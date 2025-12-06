"""Redis-based token blacklist store implementation."""

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger("auth.blacklist.redis")


class RedisTokenBlacklistStore:
    """Redis-based token blacklist with automatic TTL expiration.

    Uses Redis SETEX command for storing blacklisted token JTIs with
    automatic expiration. This is the recommended implementation for
    production multi-process deployments.

    Keys are stored with a prefix to avoid collisions with other Redis data.
    The value stored is minimal ("1") since only key existence matters.
    """

    def __init__(self, redis_client: Redis, key_prefix: str = "jwt:blacklist:") -> None:
        """Initialize the Redis blacklist store.

        Args:
            redis_client: Async Redis client instance.
            key_prefix: Prefix for blacklist keys (default: "jwt:blacklist:").
        """
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def add(self, token_jti: str, expires_in_seconds: int) -> None:
        """Add a token JTI to the blacklist with automatic expiration.

        Uses Redis SETEX to store the JTI with TTL. The entry automatically
        expires and is removed by Redis.

        Args:
            token_jti: The JWT ID to blacklist.
            expires_in_seconds: TTL for the Redis key.
        """
        key = f"{self._key_prefix}{token_jti}"
        await self._redis.setex(key, expires_in_seconds, "1")
        logger.debug(
            "token_blacklisted",
            jti=token_jti,
            expires_in=expires_in_seconds,
            store="redis",
        )

    async def is_blacklisted(self, token_jti: str) -> bool:
        """Check if a token JTI is blacklisted.

        Args:
            token_jti: The JWT ID to check.

        Returns:
            True if the key exists in Redis, False otherwise.
        """
        key = f"{self._key_prefix}{token_jti}"
        result = await self._redis.exists(key)
        return bool(result)
