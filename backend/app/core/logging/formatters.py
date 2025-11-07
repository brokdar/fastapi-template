"""Custom formatters for structured logging.

This module provides formatters that ensure consistent log output format:
timestamp, logger_name, level, message, remaining_values
"""

import structlog

from .constants import LoggingConstants


def create_ordered_console_renderer(
    colors: bool = True,
) -> structlog.dev.ConsoleRenderer:
    """Create a ConsoleRenderer with ordered columns.

    Orders columns as: timestamp, logger, level, event, then all others.

    Args:
        colors: Whether to use colored output

    Returns:
        Configured ConsoleRenderer with ordered columns
    """
    temp_renderer = structlog.dev.ConsoleRenderer(colors=colors)
    styles = temp_renderer._styles
    level_to_color = temp_renderer.get_default_level_styles(colors).copy()
    for key in level_to_color:
        level_to_color[key] += styles.bright

    columns = [
        structlog.dev.Column(
            "timestamp",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=styles.timestamp,
                reset_style=styles.reset,
                value_repr=str,
            ),
        ),
        structlog.dev.Column(
            "logger",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=styles.bright + styles.logger_name,
                reset_style=styles.reset,
                value_repr=str,
                prefix="[",
                postfix="]",
            ),
        ),
        structlog.dev.Column(
            "level",
            structlog.dev.LogLevelColumnFormatter(
                level_to_color,
                reset_style=styles.reset,
                width=0,
            ),
        ),
        structlog.dev.Column(
            "event",
            structlog.dev.KeyValueColumnFormatter(
                key_style=None,
                value_style=styles.bright,
                reset_style=styles.reset,
                value_repr=str,
                width=LoggingConstants.DEFAULT_EVENT_WIDTH,
            ),
        ),
        structlog.dev.Column(
            "",
            temp_renderer._default_column_formatter,
        ),
    ]

    return structlog.dev.ConsoleRenderer(
        columns=columns,
    )
