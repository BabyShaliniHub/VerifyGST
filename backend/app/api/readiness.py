from fastapi import APIRouter, Response

from app.db.session import IntegrationState, check_database
from app.graph.client import check_graph
from app.schemas.readiness import ComponentStatus, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/ready", response_model=ReadinessResponse)
def ready(response: Response) -> ReadinessResponse:
    """Readiness: are the dependencies reachable? /health only says the process is running."""
    checks = {"postgres": check_database(), "neo4j": check_graph()}
    is_ready = all(check.state is IntegrationState.CONNECTED for check in checks.values())
    if not is_ready:
        response.status_code = 503
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        components=[
            ComponentStatus(name=name, state=check.state.value, detail=check.detail)
            for name, check in checks.items()
        ],
    )
