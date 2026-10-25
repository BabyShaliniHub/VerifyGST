import pytest
from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.db.session import DatabaseCheck, IntegrationState, build_url, check_database
from app.main import create_app

SECRET = "s3cret-value"


def unreachable_settings(**overrides) -> Settings:
    values = dict(postgres_host="127.0.0.1", postgres_port=59999, postgres_password=SECRET)
    values.update(overrides)
    return Settings(**values)


def skip_if_postgres_is_down():
    if check_database().state is IntegrationState.UNAVAILABLE:
        pytest.skip("PostgreSQL is not running. Start it with: docker compose up -d")


def client_with_database(monkeypatch, state, detail) -> TestClient:
    monkeypatch.setattr("app.api.readiness.check_database", lambda: DatabaseCheck(state, detail))
    return TestClient(create_app())


def test_the_password_is_hidden_from_printed_settings_and_urls():
    settings = unreachable_settings()
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
    assert SECRET not in str(build_url(settings))
    assert build_url(settings).password == SECRET


def test_a_missing_password_is_reported_as_not_configured():
    result = check_database(unreachable_settings(postgres_password=""))
    assert result.state is IntegrationState.NOT_CONFIGURED


def test_an_unreachable_database_is_unavailable_and_the_result_leaks_nothing():
    result = check_database(unreachable_settings())
    assert result.state is IntegrationState.UNAVAILABLE
    for secret_text in (SECRET, "59999", "127.0.0.1"):
        assert secret_text not in result.detail


def test_the_local_database_accepts_the_settings_from_env():
    skip_if_postgres_is_down()
    result = check_database()
    assert result.state is IntegrationState.CONNECTED, result.detail


def test_a_wrong_password_is_refused_and_reported_as_authentication_failed():
    skip_if_postgres_is_down()
    result = check_database(Settings(postgres_password="definitely-not-the-password"))
    assert result.state is IntegrationState.AUTHENTICATION_FAILED, result.detail


def test_ready_reports_200_when_the_database_is_connected(monkeypatch):
    client = client_with_database(monkeypatch, IntegrationState.CONNECTED, "The database answered a test query.")
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["components"] == [
        {"name": "postgres", "state": "connected", "detail": "The database answered a test query."}
    ]


def test_ready_reports_503_when_the_database_is_down_but_health_stays_up(monkeypatch):
    client = client_with_database(monkeypatch, IntegrationState.UNAVAILABLE, "The database could not be reached.")
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["components"][0]["state"] == "unavailable"
    assert client.get("/health").status_code == 200


def test_ready_never_treats_any_failure_state_as_ready(monkeypatch):
    for state in (
        IntegrationState.NOT_CONFIGURED,
        IntegrationState.AUTHENTICATION_FAILED,
        IntegrationState.ERROR,
        IntegrationState.UNAVAILABLE,
    ):
        client = client_with_database(monkeypatch, state, "x")
        assert client.get("/ready").status_code == 503, state
