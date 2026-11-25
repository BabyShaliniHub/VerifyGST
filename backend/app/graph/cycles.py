"""Bounded search for directed cycles of SOLD_TO transactions.

A cycle is an indicator that deserves a human look, not proof of wrongdoing: companies in the
same group, or in a genuine barter or rebate arrangement, can legitimately trade in a loop.

The search is bounded three ways so it cannot run away on a large graph: a minimum and maximum
cycle length, a maximum number of cycles returned, and a time limit on every query. When the
result limit is reached the answer says so (`truncated`); it never pretends to be complete.
A query that exceeds the time limit raises an error instead of returning a partial list.

Every cycle is simple (no company appears twice) and is reported once, starting from its
smallest company id, so the same loop is never listed under several rotations.
"""

from dataclasses import dataclass

from neo4j import Driver, Query

MIN_CYCLE_LENGTH = 2
MAX_CYCLE_LENGTH = 8
MAX_RESULTS_LIMIT = 500


def _cycle_query(length: int) -> str:
    # Cypher cannot take a relationship length as a parameter. `length` is an int from the fixed
    # range below, never user input, so it is safe to place in the text. Everything else is a parameter.
    return f"""
MATCH p = (a:Company)-[:SOLD_TO*{length}]->(a)
WITH [n IN nodes(p)[0..-1] | n.id] AS company_ids, [r IN relationships(p) | r.id] AS transaction_ids
WHERE ALL(i IN range(1, size(company_ids) - 1) WHERE company_ids[0] < company_ids[i])
  AND ALL(i IN range(0, size(company_ids) - 1) WHERE NOT company_ids[i] IN company_ids[0..i])
RETURN company_ids, transaction_ids
ORDER BY company_ids
LIMIT $limit
"""


_QUERIES = {length: _cycle_query(length) for length in range(MIN_CYCLE_LENGTH, MAX_CYCLE_LENGTH + 1)}


@dataclass(frozen=True)
class Cycle:
    company_ids: tuple[str, ...]  # in trade order, starting from the smallest id
    transaction_ids: tuple[str, ...]  # transaction i goes from company i to company i + 1 (wrapping)

    @property
    def length(self) -> int:
        return len(self.company_ids)


@dataclass(frozen=True)
class CycleSearch:
    cycles: tuple[Cycle, ...]
    min_length: int
    max_length: int
    truncated: bool  # True when more cycles exist than max_results allowed


def _check_int(name: str, value: object, low: int, high: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a whole number")
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")


def find_cycles(
    driver: Driver,
    *,
    min_length: int = 3,
    max_length: int = 6,
    max_results: int = 50,
    timeout_seconds: float = 5.0,
) -> CycleSearch:
    _check_int("min_length", min_length, MIN_CYCLE_LENGTH, MAX_CYCLE_LENGTH)
    _check_int("max_length", max_length, MIN_CYCLE_LENGTH, MAX_CYCLE_LENGTH)
    _check_int("max_results", max_results, 1, MAX_RESULTS_LIMIT)
    if min_length > max_length:
        raise ValueError("min_length must not be larger than max_length")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 60:
        raise ValueError("timeout_seconds must be a number between 0 and 60")

    found: list[Cycle] = []
    with driver.session() as session:
        for length in range(min_length, max_length + 1):
            room = max_results + 1 - len(found)  # one extra row tells us whether we cut anything off
            query = Query(_QUERIES[length], timeout=timeout_seconds)
            for record in session.run(query, limit=room):
                found.append(Cycle(tuple(record["company_ids"]), tuple(record["transaction_ids"])))
            if len(found) > max_results:
                break

    truncated = len(found) > max_results
    ordered = sorted(found, key=lambda cycle: (cycle.length, cycle.company_ids))[:max_results]
    return CycleSearch(tuple(ordered), min_length, max_length, truncated)
