import uuid

import pytest
from sqlalchemy import text

from app.core.settings import get_settings
from app.db.session import IntegrationState, check_database, create_db_engine
from app.graph.client import check_graph, create_driver
from app.graph.sync import compare_stores
from app.seed.demo_data import COMPANIES, TRANSACTIONS, stable_id
from app.seed.run import run_seed

DEMO_COMPANY_IDS = [str(stable_id("company", c.key)) for c in COMPANIES]
DEMO_TRANSACTION_IDS = [str(stable_id("transaction", t.key)) for t in TRANSACTIONS]
CYCLE_COMPANY_IDS = {str(stable_id("company", key)) for key in ("C1", "C2", "C3", "C4", "C5", "C6")}


@pytest.fixture(scope="module")
def first_run():
    """Seeds the demo data once. Seeding is idempotent, so this leaves both stores consistent."""
    if (
        check_database().state is not IntegrationState.CONNECTED
        or check_graph().state is not IntegrationState.CONNECTED
    ):
        pytest.skip("PostgreSQL and Neo4j must both be running. Start them with: scripts\\dev-up.ps1")
    return run_seed(audit=False)


@pytest.fixture
def stores(first_run):
    engine = create_db_engine(get_settings())
    driver = create_driver(get_settings())
    yield engine, driver
    driver.close()
    engine.dispose()


def test_the_two_stores_agree_after_seeding(first_run):
    comparison = first_run.comparison
    assert comparison.agree, (comparison.only_in_postgres, comparison.only_in_graph)
    assert comparison.postgres_companies >= len(COMPANIES)
    assert comparison.postgres_transactions >= len(TRANSACTIONS)


def test_seeding_again_adds_nothing_and_the_stores_still_agree(first_run):
    again = run_seed(audit=False)
    assert again.seeded.companies_inserted == 0
    assert again.seeded.transactions_inserted == 0
    assert again.comparison.agree
    assert again.comparison.postgres_companies == first_run.comparison.postgres_companies
    assert again.comparison.postgres_transactions == first_run.comparison.postgres_transactions


def test_postgres_holds_the_demo_rows_marked_as_synthetic(stores):
    engine, _ = stores
    with engine.connect() as connection:
        companies = connection.execute(
            text("SELECT count(*) FROM companies WHERE is_synthetic AND id::text = ANY(:ids)"),
            {"ids": DEMO_COMPANY_IDS},
        ).scalar_one()
        transactions = connection.execute(
            text("SELECT count(*) FROM transactions WHERE is_synthetic AND id::text = ANY(:ids)"),
            {"ids": DEMO_TRANSACTION_IDS},
        ).scalar_one()
    assert companies == len(COMPANIES)
    assert transactions == len(TRANSACTIONS)


def test_every_transaction_is_a_seller_to_buyer_edge_with_exact_money(stores):
    _, driver = stores
    query = (
        "MATCH (a:Company {id: $seller})-[t:SOLD_TO {id: $edge}]->(b:Company {id: $buyer}) "
        "RETURN t.amount_minor AS minor, t.evidence_level AS level"
    )
    with driver.session() as session:
        for transaction in TRANSACTIONS:
            record = session.run(
                query,
                seller=str(stable_id("company", transaction.seller_key)),
                edge=str(stable_id("transaction", transaction.key)),
                buyer=str(stable_id("company", transaction.buyer_key)),
            ).single()
            assert record is not None, transaction.key
            assert record["minor"] == int(transaction.amount * 100), transaction.key
            assert record["level"] == transaction.evidence_level, transaction.key


def test_the_graph_contains_the_two_three_company_cycles(stores):
    _, driver = stores
    with driver.session() as session:
        found = session.run(
            "MATCH (a:Company)-[:SOLD_TO*3]->(a) RETURN collect(DISTINCT a.id) AS ids"
        ).single()["ids"]
    assert set(found) & set(DEMO_COMPANY_IDS) == CYCLE_COMPANY_IDS


def test_an_extra_graph_node_is_detected_and_not_hidden(stores):
    engine, driver = stores
    rogue = f"test-rogue-{uuid.uuid4()}"
    try:
        with driver.session() as session:
            session.run("CREATE (:Company {id: $id, name: 'Rogue'})", id=rogue).consume()
        with engine.connect() as connection:
            comparison = compare_stores(connection, driver)
        assert not comparison.agree
        assert f"company:{rogue}" in comparison.only_in_graph
    finally:
        with driver.session() as session:
            session.run("MATCH (c:Company {id: $id}) DETACH DELETE c", id=rogue).consume()
    with engine.connect() as connection:
        assert compare_stores(connection, driver).agree


def test_a_missing_graph_edge_is_detected_and_then_repaired_by_a_rebuild(stores):
    engine, driver = stores
    edge_id = str(stable_id("transaction", "T1"))
    try:
        with driver.session() as session:
            session.run("MATCH ()-[t:SOLD_TO {id: $id}]->() DELETE t", id=edge_id).consume()
        with engine.connect() as connection:
            comparison = compare_stores(connection, driver)
        assert not comparison.agree
        assert f"transaction:{edge_id}" in comparison.only_in_postgres
    finally:
        assert run_seed(audit=False).comparison.agree


def test_the_reported_insert_counts_are_never_negative(first_run):
    assert first_run.seeded.companies_inserted >= 0
    assert first_run.seeded.transactions_inserted >= 0
