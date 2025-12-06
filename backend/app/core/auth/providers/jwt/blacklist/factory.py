"""Factory for creating token blacklist store instances."""

import structlog
from pydantic import RedisDsn

from app.core.auth.providers.jwt.blacklist.memory import InMemoryTokenBlacklistStore
from app.core.auth.providers.jwt.blacklist.protocols import TokenBlacklistStore

logger = structlog.get_logger("auth.blacklist.factory")


def create_blacklist_store(redis_url: RedisDsn | None = None) -> TokenBlacklistStore:
    """Create appropriate blacklist store based on configuration.

    Creates a Redis-based store when a Redis URL is provided, otherwise
    falls back to an in-memory store. The in-memory store is suitable
    for development and testing.

    Args:
        redis_url: Redis connection URL (validated by Pydantic). If None, uses in-memory store.

    Returns:
        TokenBlacklistStore implementation (Redis or in-memory).

    Example:
        ```python
        # Production with Redis
        store = create_blacklist_store(RedisDsn("redis://localhost:6379/0"))

        # Development with in-memory
        store = create_blacklist_store()
        ```
    """
    if redis_url:
        from redis.asyncio import Redis

        from app.core.auth.providers.jwt.blacklist.redis import (
            RedisTokenBlacklistStore,
        )

        redis_client = Redis.from_url(str(redis_url))
        logger.info(
            "blacklist_store_created",
            backend="redis",
            url=_mask_redis_url(redis_url),
        )
        return RedisTokenBlacklistStore(redis_client)

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
