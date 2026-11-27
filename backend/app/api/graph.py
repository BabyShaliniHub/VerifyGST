from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection

from app.analysis.graph_view import read_graph_view
from app.api.dependencies import get_connection
from app.api.errors import translate_backend_errors
from app.schemas.graph import GraphResponse

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/graph", response_model=GraphResponse)
def get_graph(
    limit: int = Query(500, ge=1, le=2000, description="Maximum companies and transactions returned."),
    connection: Connection = Depends(get_connection),
) -> GraphResponse:
    """Companies and transactions as recorded in PostgreSQL. Does not need the graph database."""
    with translate_backend_errors():
        return read_graph_view(connection, limit)
