"""Graph schema for Neo4j.

PostgreSQL is the authoritative store. The graph is a derived copy used for path and cycle
analysis, rebuilt from PostgreSQL records. Every node and relationship carries the PostgreSQL
id in its `id` property, so the two stores can always be matched.

    (:Company {id, name})-[:SOLD_TO {id, invoice_reference, amount, currency,
                                      occurred_on, evidence_level}]->(:Company)

Neo4j Community enforces uniqueness. Existence constraints are an Enterprise feature, so
required properties are guaranteed by the code that writes the graph and by PostgreSQL.
All statements are idempotent and can be run any number of times.
"""

from neo4j import Driver

from app.core.settings import get_settings
from app.graph.client import create_driver

SCHEMA_STATEMENTS = (
    "CREATE CONSTRAINT company_id_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT sold_to_id_unique IF NOT EXISTS FOR ()-[t:SOLD_TO]-() REQUIRE t.id IS UNIQUE",
    "CREATE INDEX company_name_index IF NOT EXISTS FOR (c:Company) ON (c.name)",
    "CREATE INDEX sold_to_occurred_on_index IF NOT EXISTS FOR ()-[t:SOLD_TO]-() ON (t.occurred_on)",
)

EXPECTED_CONSTRAINTS = {"company_id_unique", "sold_to_id_unique"}
EXPECTED_INDEXES = {"company_name_index", "sold_to_occurred_on_index"}


def apply_schema(driver: Driver) -> None:
    with driver.session() as session:
        for statement in SCHEMA_STATEMENTS:
            session.run(statement).consume()


def existing_constraints(driver: Driver) -> set[str]:
    with driver.session() as session:
        return {record["name"] for record in session.run("SHOW CONSTRAINTS YIELD name")}


def existing_indexes(driver: Driver) -> set[str]:
    with driver.session() as session:
        return {record["name"] for record in session.run("SHOW INDEXES YIELD name")}


if __name__ == "__main__":
    graph_driver = create_driver(get_settings())
    try:
        apply_schema(graph_driver)
        print("Graph schema applied.")
        for name in sorted(existing_constraints(graph_driver) & EXPECTED_CONSTRAINTS):
            print("constraint:", name)
        for name in sorted(existing_indexes(graph_driver) & EXPECTED_INDEXES):
            print("index:", name)
    finally:
        graph_driver.close()
