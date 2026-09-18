"""
Health Check Endpoint.

Used by monitoring tools, load balancers, and developers to verify that the
API server is running, responsive, and properly configured.
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema for health-check response."""
    status: str
    service: str
    version: str
    timestamp: str
    debug: bool


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational status and metadata of the NGO Disaster Relief API service.",
)
def get_health() -> HealthResponse:
    """
    Returns 200 OK with server health metadata.
    """
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        debug=settings.DEBUG,
    )
