import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from sqlalchemy.exc import OperationalError

from app.api.dependencies import get_connection, get_driver
from app.api.errors import register_error_handlers
from app.main import create_app

SECRET = "secret-host-7687"


class FakeTimeout(Neo4jError):
    code = "Neo.ClientError.Transaction.TransactionTimedOut"


def raising(error):
    def fail(*args, **kwargs):
        raise error

    return fail


@pytest.fixture
def client():
    app = create_app()
    # No real database is needed here: the handlers are tested with stand-ins that fail on purpose.
    app.dependency_overrides[get_connection] = lambda: object()
    app.dependency_overrides[get_driver] = lambda: object()
    return TestClient(app, raise_server_exceptions=False)


def test_an_unreachable_graph_database_gives_503_and_leaks_nothing(client, monkeypatch):
    monkeypatch.setattr("app.api.findings.analyse_cycles", raising(ServiceUnavailable(SECRET)))
    response = client.get("/api/v1/findings")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "graph_unavailable", "message": "The graph database could not be reached."}
    }
    assert SECRET not in response.text


def test_an_unreachable_database_gives_503_and_leaks_nothing(client, monkeypatch):
    error = OperationalError("SELECT 1", {}, Exception(SECRET))
    monkeypatch.setattr("app.api.graph.read_graph_view", raising(error))
    response = client.get("/api/v1/graph")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "database_unavailable", "message": "The database could not be reached."}
    }
    assert SECRET not in response.text


def test_a_search_that_runs_out_of_time_gives_504_and_says_what_to_try(client, monkeypatch):
    monkeypatch.setattr("app.api.findings.analyse_cycles", raising(FakeTimeout(SECRET)))
    response = client.get("/api/v1/findings")
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "search_timeout"
    assert "smaller maximum cycle length" in response.json()["error"]["message"]
    assert SECRET not in response.text


def test_an_unexpected_failure_gives_a_generic_500_and_leaks_nothing(client, monkeypatch):
    monkeypatch.setattr("app.api.findings.analyse_cycles", raising(RuntimeError(SECRET)))
    response = client.get("/api/v1/findings")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong on the server."}
    }
    assert SECRET not in response.text


@pytest.mark.parametrize(
    "url, field",
    [
        ("/api/v1/findings?min_length=1", "min_length"),
        ("/api/v1/findings?max_length=99", "max_length"),
        ("/api/v1/findings?max_results=0", "max_results"),
        ("/api/v1/findings?max_results=abc", "max_results"),
        ("/api/v1/graph?limit=0", "limit"),
        ("/api/v1/graph?limit=100000", "limit"),
    ],
)
def test_invalid_parameters_give_422_with_the_field_name(client, url, field):
    response = client.get(url)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert [item["field"] for item in error["details"]] == [field]


def test_a_minimum_length_above_the_maximum_is_rejected(client):
    response = client.get("/api/v1/findings?min_length=5&max_length=3")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_only_the_new_paths_use_the_new_validation_error_shape():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/legacy")
    def legacy(n: int):
        return {"n": n}

    @app.get("/api/v1/graph")
    def graph(n: int):
        return {"n": n}

    client = TestClient(app)
    old = client.get("/legacy?n=abc")
    assert old.status_code == 422
    assert "detail" in old.json()
    assert "error" not in old.json()

    new = client.get("/api/v1/graph?n=abc")
    assert new.status_code == 422
    assert new.json()["error"]["code"] == "invalid_request"