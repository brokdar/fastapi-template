"""Logging configuration for FastAPI applications.

This module provides comprehensive logging setup with:
- Custom formatters for consistent log ordering
- Direct parameter-based configuration
- Silencing of noisy third-party loggers
- Integration with structlog
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog

from app.config import LogLevel

from .constants import LoggingConstants
from .formatters import create_ordered_console_renderer


def configure_logging(
    log_level: LogLevel = "INFO",
    log_file_path: str | None = None,
    disable_colors: bool = False,
) -> None:
    """Configure structured logging for the application.

    Sets up structlog-based logging with customizable log levels, optional file output,
    and automatic color detection for terminal environments. All logs follow a consistent
    format: timestamp, logger, level, message, remaining_values.

    Args:
        log_level (LogLevel): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to INFO.
        log_file_path (str | None): Path to log file. If specified, enables JSON file
            logging with rotation (10MB max size, 5 backups). If None (default),
            only console logging is used.
        disable_colors (bool): If True, disable colored output even in TTY environments.
            If False (default), colors are auto-detected using isatty().

    Returns:
        None

    Example:
        Development: DEBUG level with colors::

            configure_logging(log_level="DEBUG")

        Production: INFO level, no colors, with file logging::

            configure_logging(
                log_level="INFO",
                log_file_path="logs/app.log",
                disable_colors=True
            )

        CI/Testing: WARNING level, no colors::

            configure_logging(log_level="WARNING", disable_colors=True)
    """
    use_colors: bool = not disable_colors and sys.stdout.isatty()
    enable_file_logging: bool = log_file_path is not None

    if enable_file_logging and log_file_path:
        log_path: Path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    formatters: dict[str, Any] = {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                create_ordered_console_renderer(colors=use_colors),
            ],
            "foreign_pre_chain": shared_processors
            + [structlog.processors.format_exc_info],
        },
    }

    if enable_file_logging:
        formatters["json"] = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": shared_processors
            + [structlog.processors.format_exc_info],
        }

    handlers: dict[str, Any] = {
        "console": {
            "level": log_level,
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    }

    if enable_file_logging and log_file_path:
        handlers["file"] = {
            "level": log_level,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_file_path,
            "maxBytes": LoggingConstants.MAX_LOG_FILE_SIZE,
            "backupCount": LoggingConstants.LOG_FILE_BACKUP_COUNT,
            "formatter": "json",
        }

    active_handlers: list[str] = ["console"]
    if enable_file_logging:
        active_handlers.append("file")

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            "": {
                "handlers": active_handlers,
                "level": log_level,
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(logging_config)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    _silence_noisy_loggers()

    logger: structlog.BoundLogger = structlog.get_logger("logging.config")
    logger.info(
        "Logging configured",
        log_level=log_level,
        colors_enabled=use_colors,
        file_logging_enabled=enable_file_logging,
        log_file_path=log_file_path,
    )


def _silence_noisy_loggers() -> None:
    """Silence third-party loggers that generate excessive noise in application logs.

    Uvicorn loggers are completely disabled (CRITICAL level + cleared handlers) to prevent
    duplicate request logs - we handle all request logging via RequestLoggingMiddleware.
    Other libraries are set to WARNING to suppress DEBUG/INFO noise while preserving errors.
    """
    uvicorn_logger: logging.Logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.setLevel(logging.CRITICAL)

    uvicorn_access_logger: logging.Logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.setLevel(logging.CRITICAL)

    uvicorn_error_logger: logging.Logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.setLevel(logging.CRITICAL)

    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
