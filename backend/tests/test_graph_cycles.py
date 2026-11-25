import uuid

import pytest

from app.core.settings import get_settings
from app.db.session import IntegrationState, check_database
from app.graph.client import check_graph, create_driver
from app.graph.cycles import MAX_CYCLE_LENGTH, _QUERIES, find_cycles
from app.seed.demo_data import TRANSACTIONS, stable_id
from app.seed.run import run_seed


def ids(*keys, kind="company"):
    return {str(stable_id(kind, key)) for key in keys}


@pytest.fixture(scope="module")
def seeded():
    if (
        check_database().state is not IntegrationState.CONNECTED
        or check_graph().state is not IntegrationState.CONNECTED
    ):
        pytest.skip("PostgreSQL and Neo4j must both be running. Start them with: scripts\\dev-up.ps1")
    return run_seed(audit=False)


@pytest.fixture
def driver(seeded):
    graph_driver = create_driver(get_settings())
    yield graph_driver
    graph_driver.close()


def test_the_cycle_queries_are_fixed_text_with_one_parameter():
    assert sorted(_QUERIES) == list(range(2, MAX_CYCLE_LENGTH + 1))
    for length, query in _QUERIES.items():
        assert f"*{length}]" in query
        assert "$limit" in query


@pytest.mark.parametrize(
    "arguments",
    [
        {"min_length": 1},
        {"max_length": 99},
        {"min_length": 5, "max_length": 3},
        {"max_results": 0},
        {"max_results": 100000},
        {"min_length": "3"},
        {"max_length": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": 3600},
    ],
)
def test_bad_search_bounds_are_rejected_before_touching_the_database(arguments):
    with pytest.raises(ValueError):
        find_cycles(None, **arguments)


def test_the_two_demo_cycles_are_found(driver):
    result = find_cycles(driver)
    assert not result.truncated
    assert [cycle.length for cycle in result.cycles] == [3, 3]
    found = {frozenset(cycle.company_ids) for cycle in result.cycles}
    assert found == {frozenset(ids("C1", "C2", "C3")), frozenset(ids("C4", "C5", "C6"))}
    transactions = {frozenset(cycle.transaction_ids) for cycle in result.cycles}
    assert transactions == {
        frozenset(ids("T1", "T2", "T3", kind="transaction")),
        frozenset(ids("T4", "T5", "T6", kind="transaction")),
    }


def test_each_cycle_starts_at_its_smallest_id_and_follows_the_trade_direction(driver):
    endpoints = {
        str(stable_id("transaction", t.key)): (
            str(stable_id("company", t.seller_key)),
            str(stable_id("company", t.buyer_key)),
        )
        for t in TRANSACTIONS
    }
    for cycle in find_cycles(driver).cycles:
        assert cycle.company_ids[0] == min(cycle.company_ids)
        for position, transaction_id in enumerate(cycle.transaction_ids):
            seller, buyer = endpoints[transaction_id]
            assert seller == cycle.company_ids[position]
            assert buyer == cycle.company_ids[(position + 1) % cycle.length]


def test_length_bounds_that_exclude_the_demo_cycles_find_nothing(driver):
    assert find_cycles(driver, min_length=2, max_length=2).cycles == ()
    assert find_cycles(driver, min_length=4, max_length=6).cycles == ()


def test_the_result_limit_truncates_and_says_so(driver):
    one = find_cycles(driver, max_results=1)
    assert len(one.cycles) == 1
    assert one.truncated
    two = find_cycles(driver, max_results=2)
    assert len(two.cycles) == 2
    assert not two.truncated


def test_a_two_company_loop_is_found_only_when_two_is_allowed(driver):
    first, second = sorted(f"test-{uuid.uuid4()}" for _ in range(2))
    edges = [f"test-{uuid.uuid4()}" for _ in range(2)]
    try:
        with driver.session() as session:
            session.run("CREATE (:Company {id: $a}), (:Company {id: $b})", a=first, b=second).consume()
            create_edge = (
                "MATCH (x:Company {id: $x}), (y:Company {id: $y}) CREATE (x)-[:SOLD_TO {id: $edge}]->(y)"
            )
            session.run(create_edge, x=first, y=second, edge=edges[0]).consume()
            session.run(create_edge, x=second, y=first, edge=edges[1]).consume()

        with_two = find_cycles(driver, min_length=2, max_length=2)
        assert [cycle.company_ids for cycle in with_two.cycles] == [(first, second)]
        assert [cycle.transaction_ids for cycle in with_two.cycles] == [(edges[0], edges[1])]

        without_two = find_cycles(driver, min_length=3, max_length=6)
        assert all(first not in cycle.company_ids for cycle in without_two.cycles)
    finally:
        with driver.session() as session:
            session.run("MATCH (c:Company) WHERE c.id IN $ids DETACH DELETE c", ids=[first, second]).consume()
    assert find_cycles(driver, min_length=2, max_length=2).cycles == ()
