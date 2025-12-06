"""JWT token blacklist module for token revocation.

This module provides a protocol-based abstraction for token blacklist storage,
with implementations for both in-memory (development) and Redis (production)
backends.

Example:
    ```python
    from app.core.auth.providers.jwt.blacklist import (
        TokenBlacklistStore,
        create_blacklist_store,
    )

    # Create store based on configuration
    store = create_blacklist_store(redis_url="redis://localhost:6379/0")

    # Or use in-memory for development
    store = create_blacklist_store()
    ```
"""

from app.core.auth.providers.jwt.blacklist.factory import create_blacklist_store
from app.core.auth.providers.jwt.blacklist.protocols import TokenBlacklistStore

__all__ = ["TokenBlacklistStore", "create_blacklist_store"]
