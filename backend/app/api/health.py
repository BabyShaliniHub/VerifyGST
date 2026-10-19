from fastapi import APIRouter

from app.core.info import SERVICE_NAME, SERVICE_VERSION
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check: the API process is running. It says nothing about databases."""
    return HealthResponse(status="ok", service=SERVICE_NAME, version=SERVICE_VERSION)
