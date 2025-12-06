"""Redis async client management with connection pooling."""

import structlog
from pydantic import RedisDsn
from redis.asyncio import ConnectionPool, Redis

logger = structlog.get_logger("redis.client")


class RedisClient:
    """Manages Redis connection pool lifecycle.

    Implements singleton pattern for connection pooling with proper
    async context management. Initialize during application startup
    and close during shutdown.

    Example:
        ```python
        # In FastAPI lifespan
        async with lifespan(app):
            await RedisClient.initialize("redis://localhost:6379/0")
            yield
            await RedisClient.close()

        # In services
        redis = RedisClient.get()
        await redis.set("key", "value")
        ```
    """

    _pool: ConnectionPool | None = None
    _redis: Redis | None = None

    @classmethod
    async def initialize(
        cls,
        redis_url: RedisDsn | str,
        max_connections: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ) -> None:
        """Initialize Redis connection pool.

        Args:
            redis_url: Redis connection URL.
            max_connections: Maximum connections in pool.
            socket_timeout: Socket timeout in seconds.
            socket_connect_timeout: Connection timeout in seconds.

        Raises:
            ConnectionError: If Redis is unreachable.
        """
        if cls._redis is not None:
            logger.warning("redis_already_initialized")
            return

        cls._pool = ConnectionPool.from_url(
            str(redis_url),
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            decode_responses=True,
        )

        cls._redis = Redis(connection_pool=cls._pool)

        await cls._redis.ping()  # type: ignore[misc]
        logger.info(
            "redis_initialized",
            max_connections=max_connections,
            socket_timeout=socket_timeout,
        )

    @classmethod
    async def close(cls) -> None:
        """Close connection pool and all connections.

        Safe to call even if not initialized.
        """
        if cls._redis is not None:
            await cls._redis.aclose()
            cls._redis = None

        if cls._pool is not None:
            await cls._pool.disconnect()
            cls._pool = None

        logger.info("redis_closed")

    @classmethod
    def get(cls) -> Redis:
        """Get Redis client instance.

        Returns:
            Redis client with pooled connections.

        Raises:
            RuntimeError: If Redis not initialized.
        """
        if cls._redis is None:
            raise RuntimeError(
                "Redis not initialized. Ensure RedisClient.initialize() "
                "is called during application startup."
            )

        return cls._redis

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if Redis client is initialized."""
        return cls._redis is not None
