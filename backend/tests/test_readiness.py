from fastapi.testclient import TestClient

from app.db.session import DatabaseCheck, IntegrationState
from app.main import create_app

POSTGRES_OK = DatabaseCheck(IntegrationState.CONNECTED, "The database answered a test query.")
GRAPH_OK = DatabaseCheck(IntegrationState.CONNECTED, "The graph database answered a test query.")
FAILURE_STATES = (
    IntegrationState.NOT_CONFIGURED,
    IntegrationState.AUTHENTICATION_FAILED,
    IntegrationState.ERROR,
    IntegrationState.UNAVAILABLE,
)


def client_with(monkeypatch, postgres, graph) -> TestClient:
    monkeypatch.setattr("app.api.readiness.check_database", lambda: postgres)
    monkeypatch.setattr("app.api.readiness.check_graph", lambda: graph)
    return TestClient(create_app())


def states(response):
    return {c["name"]: c["state"] for c in response.json()["components"]}


def test_ready_reports_200_only_when_both_databases_are_connected(monkeypatch):
    response = client_with(monkeypatch, POSTGRES_OK, GRAPH_OK).get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert states(response) == {"postgres": "connected", "neo4j": "connected"}


def test_ready_reports_503_and_names_the_failing_component_when_postgres_is_down(monkeypatch):
    down = DatabaseCheck(IntegrationState.UNAVAILABLE, "The database could not be reached.")
    response = client_with(monkeypatch, down, GRAPH_OK).get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert states(response) == {"postgres": "unavailable", "neo4j": "connected"}


def test_ready_reports_503_and_names_the_failing_component_when_neo4j_is_down(monkeypatch):
    down = DatabaseCheck(IntegrationState.UNAVAILABLE, "The graph database could not be reached.")
    response = client_with(monkeypatch, POSTGRES_OK, down).get("/ready")
    assert response.status_code == 503
    assert states(response) == {"postgres": "connected", "neo4j": "unavailable"}


def test_no_failure_state_is_ever_treated_as_ready(monkeypatch):
    for state in FAILURE_STATES:
        failing = DatabaseCheck(state, "x")
        assert client_with(monkeypatch, failing, GRAPH_OK).get("/ready").status_code == 503, state
        assert client_with(monkeypatch, POSTGRES_OK, failing).get("/ready").status_code == 503, state


def test_health_stays_up_when_every_dependency_is_down(monkeypatch):
    down = DatabaseCheck(IntegrationState.UNAVAILABLE, "down")
    client = client_with(monkeypatch, down, down)
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200
