import pytest
from fastapi.testclient import TestClient

from app.db.session import IntegrationState, check_database
from app.graph.client import check_graph
from app.main import create_app
from app.seed.run import run_seed


@pytest.fixture(scope="module")
def client():
    if (
        check_database().state is not IntegrationState.CONNECTED
        or check_graph().state is not IntegrationState.CONNECTED
    ):
        pytest.skip("PostgreSQL and Neo4j must both be running. Start them with: scripts\\dev-up.ps1")
    run_seed(audit=False)
    return TestClient(create_app())


def test_the_graph_endpoint_returns_the_demo_companies_and_transactions(client):
    response = client.get("/api/v1/graph")
    assert response.status_code == 200
    body = response.json()
    assert len(body["companies"]) == 8
    assert len(body["transactions"]) == 9
    assert body["truncated"] == {"companies": False, "transactions": False}
    assert body["contains_synthetic_data"] is True
    assert all(company["is_synthetic"] for company in body["companies"])


def test_money_is_sent_as_exact_decimal_strings_never_as_floats(client):
    body = client.get("/api/v1/graph").json()
    amounts = {t["amount"] for t in body["transactions"]}
    assert "4800000.00" in amounts
    assert "640000.00" in amounts
    assert all(isinstance(t["amount"], str) for t in body["transactions"])


def test_the_graph_limit_truncates_and_says_so(client):
    body = client.get("/api/v1/graph?limit=3").json()
    assert len(body["companies"]) == 3
    assert len(body["transactions"]) == 3
    assert body["truncated"] == {"companies": True, "transactions": True}


def test_the_findings_endpoint_returns_the_high_priority_loop_first(client):
    response = client.get("/api/v1/findings")
    assert response.status_code == 200
    body = response.json()
    assert body["truncated"] is False
    assert [f["priority"] for f in body["findings"]] == ["high", "low"]
    high, low = body["findings"]
    assert {c["name"] for c in high["companies"]} == {"Dune Textiles", "Elm Packaging", "Fern Agro"}
    assert [s["code"] for s in high["signals"]] == [
        "evidence_gaps",
        "repeated_invoice_reference",
        "similar_amounts",
        "tight_timing",
    ]
    assert [c["result"] for c in high["checks"]] == ["triggered"] * 4
    assert low["signals"] == []
    assert [c["result"] for c in low["checks"]] == ["not_triggered"] * 4
    for finding in body["findings"]:
        assert "not proof" in finding["disclaimer"]


def test_every_company_and_transaction_in_a_finding_exists_in_the_graph_endpoint(client):
    graph = client.get("/api/v1/graph").json()
    company_ids = {c["id"] for c in graph["companies"]}
    transaction_ids = {t["id"] for t in graph["transactions"]}
    for finding in client.get("/api/v1/findings").json()["findings"]:
        assert {c["id"] for c in finding["companies"]} <= company_ids
        assert set(finding["transaction_ids"]) <= transaction_ids
        for signal in finding["signals"]:
            assert set(signal["transaction_ids"]) <= set(finding["transaction_ids"])


def test_the_findings_limit_truncates_and_says_so(client):
    body = client.get("/api/v1/findings?max_results=1").json()
    assert body["truncated"] is True
    assert len(body["findings"]) == 1


def test_a_length_range_with_no_cycles_returns_an_empty_list_not_an_error(client):
    response = client.get("/api/v1/findings?min_length=4&max_length=6")
    assert response.status_code == 200
    assert response.json()["findings"] == []
