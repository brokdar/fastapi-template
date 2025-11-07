"""FastAPI dependencies for pagination query parameters.

This module provides reusable FastAPI dependencies for handling pagination
parameters across all API endpoints.
"""

from typing import Annotated

from fastapi import Depends, Query

from .schemas import PaginationParams


async def pagination_params(
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of items to return")
    ] = 10,
) -> PaginationParams:
    """Create pagination parameters from query string.

    Args:
        offset: Number of items to skip (0-based, default: 0)
        limit: Maximum number of items to return (1-100, default: 10)

    Returns:
        PaginationParams instance with validated pagination settings

    Usage:
        ```python
        @router.get("/items/")
        async def get_items(
            pagination: Annotated[PaginationParams, Depends(pagination_params)],
        ):
            # Use pagination.offset, pagination.limit
        ```
    """
    return PaginationParams(offset=offset, limit=limit)


PaginationDependency = Annotated[PaginationParams, Depends(pagination_params)]
