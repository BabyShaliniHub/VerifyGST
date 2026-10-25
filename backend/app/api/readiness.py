from fastapi import APIRouter, Response

from app.db.session import IntegrationState, check_database
from app.schemas.readiness import ComponentStatus, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/ready", response_model=ReadinessResponse)
def ready(response: Response) -> ReadinessResponse:
    """Readiness: are the dependencies reachable? /health only says the process is running."""
    database = check_database()
    is_ready = database.state is IntegrationState.CONNECTED
    if not is_ready:
        response.status_code = 503
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        components=[ComponentStatus(name="postgres", state=database.state.value, detail=database.detail)],
    )
