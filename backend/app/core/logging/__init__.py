"""FastAPI logging system with structured logging and request tracking.

This package provides:
- configure_logging: Simple, parameter-based logging configuration
- RequestLoggingMiddleware: Automatic request tracking with unique IDs
- get_request_id, get_request_logger: Utility functions for request-bound logging
"""

from .config import configure_logging
from .middleware import RequestLoggingMiddleware
from .utils import get_request_id, get_request_logger

__all__ = [
    "configure_logging",
    "RequestLoggingMiddleware",
    "get_request_id",
    "get_request_logger",
]
