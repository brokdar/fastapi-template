"""Constants for the logging system."""


class LoggingConstants:
    """Centralized constants for logging configuration."""

    # Request ID configuration
    REQUEST_ID_LENGTH = 12
    REQUEST_ID_PREFIX = "req_"

    # File logging configuration
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT = 5

    # Formatter configuration
    DEFAULT_EVENT_WIDTH = 30

    # Common excluded routes for middleware
    # Supports exact paths and wildcard patterns:
    # - Exact: "/health", "/ping"
    # - Suffix wildcard: "*/health" (matches /api/health, /v1/health)
    # - Prefix wildcard: "/api/*" (matches /api/users, /api/posts)
    # - Complex: "/api/*/health" (matches /api/v1/health, /api/v2/health)
    COMMON_EXCLUDED_ROUTES = [
        "*/health",
        "*/ping",
        "*/metrics",
        "*/docs",
        "*/redoc",
        "*/openapi.json",
        "*/favicon.ico",
    ]
