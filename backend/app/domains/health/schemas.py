from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for the health check endpoint."""

    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
