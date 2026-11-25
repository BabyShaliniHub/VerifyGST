"""Seed the demonstration data and build the matching graph.

    python -m app.seed.run

Safe to run any number of times. It loads the synthetic rows into PostgreSQL, rebuilds the
Neo4j graph from PostgreSQL, and checks that the two stores agree.
"""

from dataclasses import dataclass

from app.core.settings import get_settings
from app.db.session import IntegrationState, check_database, create_db_engine
from app.graph.client import check_graph, create_driver
from app.graph.schema import apply_schema
from app.graph.sync import Comparison, compare_stores, read_postgres_rows, rebuild_graph
from app.seed.loader import SeedResult, seed_postgres


@dataclass(frozen=True)
class SeedRun:
    seeded: SeedResult
    comparison: Comparison


def run_seed(*, audit: bool = True) -> SeedRun:
    settings = get_settings()
    engine = create_db_engine(settings)
    driver = create_driver(settings)
    try:
        apply_schema(driver)
        with engine.begin() as connection:
            seeded = seed_postgres(connection, audit=audit)
        with engine.connect() as connection:
            rebuild_graph(driver, read_postgres_rows(connection))
        with engine.connect() as connection:
            comparison = compare_stores(connection, driver)
    finally:
        driver.close()
        engine.dispose()
    return SeedRun(seeded, comparison)


def main() -> int:
    for name, check in (("PostgreSQL", check_database()), ("Neo4j", check_graph())):
        if check.state is not IntegrationState.CONNECTED:
            print(f"{name} is not ready ({check.state.value}). Start the databases with scripts\\dev-up.ps1 and try again.")
            return 2

    run = run_seed()
    c = run.comparison
    print(
        f"PostgreSQL: {c.postgres_companies} companies, {c.postgres_transactions} transactions "
        f"(added this run: {run.seeded.companies_inserted} and {run.seeded.transactions_inserted})"
    )
    print(f"Neo4j:      {c.graph_companies} companies, {c.graph_transactions} transactions")
    if c.agree:
        print("The two stores agree.")
        return 0
    print("The two stores DISAGREE:")
    for item in c.only_in_postgres:
        print("  only in PostgreSQL:", item)
    for item in c.only_in_graph:
        print("  only in Neo4j:", item)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
