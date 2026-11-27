from collections.abc import Iterator
from functools import lru_cache

from neo4j import Driver
from sqlalchemy import Connection
from sqlalchemy.exc import InterfaceError, OperationalError

from app.api.errors import ApiError
from app.core.settings import get_settings
from app.db.session import get_engine
from app.graph.client import create_driver


@lru_cache
def _graph_driver() -> Driver:
    # One driver for the whole process: it keeps a small connection pool and connects lazily.
    return create_driver(get_settings())


def get_driver() -> Driver:
    return _graph_driver()


def get_connection() -> Iterator[Connection]:
    try:
        connection = get_engine().connect()
    except (OperationalError, InterfaceError) as exc:
        raise ApiError(503, "database_unavailable", "The database could not be reached.") from exc
    try:
        yield connection
    finally:
        connection.close()
