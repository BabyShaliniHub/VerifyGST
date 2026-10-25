"""Database engine and connection check.

check_database() never raises and never puts a host, user, password or driver message into
its result. The states match the integration states shown in Settings.
"""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.settings import Settings, get_settings

# PostgreSQL error codes for a wrong password or a refused login.
_AUTH_FAILED_SQLSTATES = {"28P01", "28000"}


def build_url(settings: Settings) -> URL:
    """Build the connection URL from parts, so special characters never need escaping."""
    return URL.create(
        "postgresql+psycopg",
        username=settings.postgres_user,
        password=settings.postgres_password.get_secret_value(),
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(build_url(settings), pool_pre_ping=True, connect_args={"connect_timeout": 3})


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings())


class IntegrationState(str, Enum):
    CONNECTED = "connected"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    ERROR = "error"


@dataclass(frozen=True)
class DatabaseCheck:
    state: IntegrationState
    detail: str


def _is_auth_failure(error: OperationalError) -> bool:
    """True when the server answered and refused the login.

    Errors raised while connecting carry no SQLSTATE, so the server's message is checked as
    well. The message is only used to pick a state. It is never shown.
    """
    if getattr(error.orig, "sqlstate", None) in _AUTH_FAILED_SQLSTATES:
        return True
    message = str(error.orig).lower()
    return "password authentication failed" in message or "no pg_hba.conf entry" in message


def check_database(settings: Settings | None = None) -> DatabaseCheck:
    settings = settings or get_settings()
    if not settings.postgres_password.get_secret_value():
        return DatabaseCheck(IntegrationState.NOT_CONFIGURED, "The database password is not set.")

    engine = create_db_engine(settings)  # a fresh engine, so a cached one can never hide a bad setting
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as error:
        if _is_auth_failure(error):
            return DatabaseCheck(IntegrationState.AUTHENTICATION_FAILED, "The database refused the login.")
        return DatabaseCheck(IntegrationState.UNAVAILABLE, "The database could not be reached.")
    except SQLAlchemyError:
        return DatabaseCheck(IntegrationState.ERROR, "The database check failed.")
    finally:
        engine.dispose()
    return DatabaseCheck(IntegrationState.CONNECTED, "The database answered a test query.")
