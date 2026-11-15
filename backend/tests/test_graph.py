import uuid

import pytest
from neo4j.exceptions import ConstraintError

from app.core.settings import Settings
from app.db.session import IntegrationState
from app.graph.client import check_graph, create_driver
from app.graph.schema import (
    EXPECTED_CONSTRAINTS,
    EXPECTED_INDEXES,
    apply_schema,
    existing_constraints,
    existing_indexes,
)

SECRET = "s3cret-graph-value"


@pytest.fixture
def driver():
    if check_graph().state is IntegrationState.UNAVAILABLE:
        pytest.skip("Neo4j is not running. Start it with: docker compose up -d")
    graph_driver = create_driver(Settings())
    apply_schema(graph_driver)
    yield graph_driver
    graph_driver.close()


def count_companies(graph_driver, company_id) -> int:
    with graph_driver.session() as session:
        record = session.run("MATCH (c:Company {id: $id}) RETURN count(c) AS n", id=company_id).single()
        return record["n"]


def test_the_graph_password_is_hidden_from_printed_settings():
    settings = Settings(neo4j_password=SECRET)
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)


def test_a_missing_graph_password_is_reported_as_not_configured():
    assert check_graph(Settings(neo4j_password="")).state is IntegrationState.NOT_CONFIGURED


def test_an_unreachable_graph_database_is_unavailable_and_the_result_leaks_nothing():
    result = check_graph(Settings(neo4j_uri="bolt://127.0.0.1:59998", neo4j_password=SECRET))
    assert result.state is IntegrationState.UNAVAILABLE
    for secret_text in (SECRET, "59998", "127.0.0.1"):
        assert secret_text not in result.detail


def test_a_malformed_graph_address_is_an_error_not_a_crash():
    result = check_graph(Settings(neo4j_uri="not-a-uri", neo4j_password=SECRET))
    assert result.state is IntegrationState.ERROR


def test_the_local_graph_database_accepts_the_settings_from_env():
    if check_graph().state is IntegrationState.UNAVAILABLE:
        pytest.skip("Neo4j is not running. Start it with: docker compose up -d")
    result = check_graph()
    assert result.state is IntegrationState.CONNECTED, result.detail


def test_a_wrong_graph_password_is_refused_and_reported_as_authentication_failed():
    if check_graph().state is IntegrationState.UNAVAILABLE:
        pytest.skip("Neo4j is not running. Start it with: docker compose up -d")
    result = check_graph(Settings(neo4j_password="definitely-not-the-password"))
    assert result.state is IntegrationState.AUTHENTICATION_FAILED, result.detail


def test_the_schema_can_be_applied_twice_and_creates_the_expected_names(driver):
    apply_schema(driver)
    assert EXPECTED_CONSTRAINTS <= existing_constraints(driver)
    assert EXPECTED_INDEXES <= existing_indexes(driver)


def delete_test_nodes(graph_driver, company_ids):
    with graph_driver.session() as session:
        session.run("MATCH (c:Company) WHERE c.id IN $ids DETACH DELETE c", ids=company_ids).consume()


def test_a_company_id_cannot_exist_twice(driver):
    company_id = f"test-{uuid.uuid4()}"
    try:
        with driver.session() as session:
            session.run("CREATE (:Company {id: $id, name: 'First'})", id=company_id).consume()
            with pytest.raises(ConstraintError):
                session.run("CREATE (:Company {id: $id, name: 'Second'})", id=company_id).consume()
        assert count_companies(driver, company_id) == 1
    finally:
        delete_test_nodes(driver, [company_id])
    assert count_companies(driver, company_id) == 0


def test_a_transaction_id_cannot_exist_twice(driver):
    company_ids = [f"test-{uuid.uuid4()}" for _ in range(2)]
    edge_id = f"test-{uuid.uuid4()}"
    create_edge = (
        "MATCH (a:Company {id: $a}), (b:Company {id: $b}) "
        "CREATE (a)-[:SOLD_TO {id: $edge}]->(b)"
    )
    try:
        with driver.session() as session:
            for company_id in company_ids:
                session.run("CREATE (:Company {id: $id})", id=company_id).consume()
            session.run(create_edge, a=company_ids[0], b=company_ids[1], edge=edge_id).consume()
            with pytest.raises(ConstraintError):
                session.run(create_edge, a=company_ids[1], b=company_ids[0], edge=edge_id).consume()
            count = session.run(
                "MATCH ()-[t:SOLD_TO {id: $edge}]->() RETURN count(t) AS n", edge=edge_id
            ).single()["n"]
            assert count == 1
    finally:
        delete_test_nodes(driver, company_ids)
    assert count_companies(driver, company_ids[0]) == 0