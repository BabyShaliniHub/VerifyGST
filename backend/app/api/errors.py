"""One error format for the graph and findings endpoints:

    {"error": {"code": "...", "message": "...", "details": [...]}}

Messages are fixed text. They never contain addresses, credentials, driver messages or request
input, so a failure cannot leak anything. The older verification endpoints keep their existing
error shape until the frontend is moved over.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from neo4j.exceptions import AuthError, Neo4jError, ServiceUnavailable, SessionExpired
from sqlalchemy.exc import InterfaceError, OperationalError

logger = logging.getLogger("verifigst.api")

# Only these paths use the new validation error shape.
CONSISTENT_ERROR_PATHS = ("/api/v1/graph", "/api/v1/findings")


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str, details: list[dict] | None = None) -> dict:
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


@contextmanager
def translate_backend_errors() -> Iterator[None]:
    """Turn database and graph failures into safe, typed API errors."""
    try:
        yield
    except ApiError:
        raise
    except (OperationalError, InterfaceError) as exc:
        raise ApiError(503, "database_unavailable", "The database could not be reached.") from exc
    except (AuthError, ServiceUnavailable, SessionExpired) as exc:
        raise ApiError(503, "graph_unavailable", "The graph database could not be reached.") from exc
    except Neo4jError as exc:
        if "TimedOut" in (exc.code or ""):
            raise ApiError(
                504,
                "search_timeout",
                "The search took too long and was stopped. Try a smaller maximum cycle length.",
            ) from exc
        raise


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        if request.url.path not in CONSISTENT_ERROR_PATHS:
            return await request_validation_exception_handler(request, exc)
        details = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_body("invalid_request", "The request has invalid parameters.", details),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Something went wrong on the server."),
        )
