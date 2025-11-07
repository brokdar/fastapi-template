"""Generic pagination schemas for FastAPI applications.

This module provides reusable pagination schemas that can be used
across all domains to eliminate code duplication and ensure consistent API responses.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PaginationMeta(BaseModel):
    """Pagination metadata for all paginated responses."""

    offset: int = Field(ge=0, description="Number of items skipped")
    limit: int = Field(ge=1, le=100, description="Maximum items returned")
    total: int = Field(ge=0, description="Total number of items")
    has_next: bool = Field(description="Whether there are more items")
    has_prev: bool = Field(description="Whether there are previous items")


class Page[T](BaseModel):
    """Generic pagination response wrapping any list of items."""

    items: list[T] = Field(description="List of items for current request")
    pagination: PaginationMeta = Field(description="Pagination metadata")

    @classmethod
    def create(cls, items: list[T], offset: int, limit: int, total: int) -> Page[T]:
        """Factory method to create a Page with calculated metadata.

        Args:
            items: List of items for the current request
            offset: Number of items skipped
            limit: Maximum number of items returned
            total: Total number of items available

        Returns:
            Page instance with calculated pagination metadata
        """
        return cls(
            items=items,
            pagination=PaginationMeta(
                offset=offset,
                limit=limit,
                total=total,
                has_next=offset + limit < total,
                has_prev=offset > 0,
            ),
        )


class PaginationParams(BaseModel):
    """Pagination query parameters with validation."""

    model_config = ConfigDict(extra="forbid")

    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of items to return"
    )
