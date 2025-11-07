from fastapi import status
from fastapi.routing import APIRouter

from .schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Endpoint to check if the service is up and running",
)
async def health_check() -> HealthResponse:
    """Check if the service is healthy and return its current status."""
    return HealthResponse(status="healthy")
