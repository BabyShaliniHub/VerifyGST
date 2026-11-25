import pytest

from app.analysis.service import analyse_cycles
from app.core.settings import get_settings
from app.db.session import IntegrationState, check_database, create_db_engine
from app.graph.client import check_graph, create_driver
from app.seed.run import run_seed


@pytest.fixture(scope="module")
def seeded():
    if (
        check_database().state is not IntegrationState.CONNECTED
        or check_graph().state is not IntegrationState.CONNECTED
    ):
        pytest.skip("PostgreSQL and Neo4j must both be running. Start them with: scripts\\dev-up.ps1")
    return run_seed(audit=False)


@pytest.fixture
def stores(seeded):
    engine = create_db_engine(get_settings())
    driver = create_driver(get_settings())
    yield engine, driver
    driver.close()
    engine.dispose()


def test_the_demo_data_produces_one_high_and_one_low_priority_finding(stores):
    engine, driver = stores
    with engine.connect() as connection:
        result = analyse_cycles(connection, driver)
    assert not result.truncated
    assert [f.priority for f in result.findings] == ["high", "low"]
    high, low = result.findings
    assert set(high.company_names) == {"Dune Textiles", "Elm Packaging", "Fern Agro"}
    assert set(low.company_names) == {"Alder Traders", "Birch Metals", "Cedar Logistics"}
    assert [s.code for s in high.signals] == [
        "evidence_gaps",
        "repeated_invoice_reference",
        "similar_amounts",
        "tight_timing",
    ]
    assert low.signals == ()
    assert low.not_evaluated == ()


def test_a_search_that_cannot_reach_the_cycles_returns_no_findings(stores):
    engine, driver = stores
    with engine.connect() as connection:
        result = analyse_cycles(connection, driver, min_length=4, max_length=6)
    assert result.findings == ()
    assert not result.truncated


def test_a_result_limit_is_reported_to_the_caller(stores):
    engine, driver = stores
    with engine.connect() as connection:
        result = analyse_cycles(connection, driver, max_results=1)
    assert result.truncated
    assert len(result.findings) == 1
