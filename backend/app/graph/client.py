"""Neo4j driver and connection check.

check_graph() never raises and never puts an address, user, password or driver message into
its result. It reuses the same states as the PostgreSQL check.
"""

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from app.core.settings import Settings, get_settings
from app.db.session import DatabaseCheck, IntegrationState


def create_driver(settings: Settings) -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        connection_timeout=3,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=3,
    )


def check_graph(settings: Settings | None = None) -> DatabaseCheck:
    settings = settings or get_settings()
    if not settings.neo4j_password.get_secret_value():
        return DatabaseCheck(IntegrationState.NOT_CONFIGURED, "The graph database password is not set.")

    try:
        driver = create_driver(settings)
    except Exception:  # a malformed address or option
        return DatabaseCheck(IntegrationState.ERROR, "The graph database settings are not valid.")

    try:
        driver.verify_connectivity()
    except AuthError:
        return DatabaseCheck(IntegrationState.AUTHENTICATION_FAILED, "The graph database refused the login.")
    except ServiceUnavailable:
        return DatabaseCheck(IntegrationState.UNAVAILABLE, "The graph database could not be reached.")
    except Exception:
        return DatabaseCheck(IntegrationState.ERROR, "The graph database check failed.")
    finally:
        driver.close()
    return DatabaseCheck(IntegrationState.CONNECTED, "The graph database answered a test query.")
