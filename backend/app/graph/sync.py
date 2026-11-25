"""Keep the Neo4j graph in step with PostgreSQL.

PostgreSQL is authoritative. The graph is a derived copy: rebuild_graph() deletes every Company
node and SOLD_TO relationship and recreates them from PostgreSQL rows, so the graph can never
hold anything PostgreSQL does not. Ids are the PostgreSQL ids as text. Money is stored as
integer minor units (paise), because Neo4j has no exact decimal type.
"""

from dataclasses import dataclass
from decimal import Decimal

from neo4j import Driver
from sqlalchemy import Connection, text

_CREATE_COMPANIES = """
UNWIND $rows AS row
CREATE (c:Company {id: row.id, name: row.name, domain: row.domain, is_synthetic: row.is_synthetic})
"""

_CREATE_EDGES = """
UNWIND $rows AS row
MATCH (a:Company {id: row.seller_id}), (b:Company {id: row.buyer_id})
CREATE (a)-[:SOLD_TO {
    id: row.id,
    invoice_reference: row.invoice_reference,
    amount_minor: row.amount_minor,
    currency: row.currency,
    occurred_on: row.occurred_on,
    evidence_level: row.evidence_level,
    is_synthetic: row.is_synthetic
}]->(b)
"""


def to_minor_units(amount: Decimal) -> int:
    """4790000.00 becomes 479000000 (paise)."""
    return int((amount * 100).to_integral_value())


@dataclass(frozen=True)
class PostgresRows:
    companies: list[dict]
    transactions: list[dict]


def read_postgres_rows(connection: Connection) -> PostgresRows:
    companies = [
        {"id": str(r.id), "name": r.name, "domain": r.domain, "is_synthetic": r.is_synthetic}
        for r in connection.execute(
            text("SELECT id, name, domain, is_synthetic FROM companies ORDER BY name")
        )
    ]
    transactions = [
        {
            "id": str(r.id),
            "seller_id": str(r.seller_company_id),
            "buyer_id": str(r.buyer_company_id),
            "invoice_reference": r.invoice_reference,
            "amount_minor": to_minor_units(r.amount),
            "currency": r.currency,
            "occurred_on": r.occurred_on,
            "evidence_level": r.evidence_level,
            "is_synthetic": r.is_synthetic,
        }
        for r in connection.execute(
            text(
                "SELECT id, seller_company_id, buyer_company_id, invoice_reference, amount, "
                "currency, occurred_on, evidence_level, is_synthetic "
                "FROM transactions ORDER BY occurred_on, id"
            )
        )
    ]
    return PostgresRows(companies, transactions)


def rebuild_graph(driver: Driver, rows: PostgresRows) -> None:
    """Replace the whole company graph with a fresh copy of the PostgreSQL rows, in one transaction."""

    def work(transaction):
        transaction.run("MATCH (c:Company) DETACH DELETE c").consume()
        transaction.run(_CREATE_COMPANIES, rows=rows.companies).consume()
        transaction.run(_CREATE_EDGES, rows=rows.transactions).consume()

    with driver.session() as session:
        session.execute_write(work)


def read_graph(driver: Driver) -> tuple[set[str], set[tuple]]:
    with driver.session() as session:
        companies = {r["id"] for r in session.run("MATCH (c:Company) RETURN c.id AS id")}
        edges = {
            (r["id"], r["seller"], r["buyer"], r["amount_minor"])
            for r in session.run(
                "MATCH (a:Company)-[t:SOLD_TO]->(b:Company) "
                "RETURN t.id AS id, a.id AS seller, b.id AS buyer, t.amount_minor AS amount_minor"
            )
        }
    return companies, edges


@dataclass(frozen=True)
class Comparison:
    postgres_companies: int
    graph_companies: int
    postgres_transactions: int
    graph_transactions: int
    only_in_postgres: tuple[str, ...]
    only_in_graph: tuple[str, ...]

    @property
    def agree(self) -> bool:
        return not self.only_in_postgres and not self.only_in_graph


def compare_stores(connection: Connection, driver: Driver) -> Comparison:
    """Compare ids, endpoints and amounts. A difference is reported, never silently fixed."""
    rows = read_postgres_rows(connection)
    pg_companies = {c["id"] for c in rows.companies}
    pg_edges = {(t["id"], t["seller_id"], t["buyer_id"], t["amount_minor"]) for t in rows.transactions}
    graph_companies, graph_edges = read_graph(driver)

    only_in_postgres = [f"company:{i}" for i in sorted(pg_companies - graph_companies)]
    only_in_postgres += [f"transaction:{e[0]}" for e in sorted(pg_edges - graph_edges)]
    only_in_graph = [f"company:{i}" for i in sorted(graph_companies - pg_companies)]
    only_in_graph += [f"transaction:{e[0]}" for e in sorted(graph_edges - pg_edges)]

    return Comparison(
        postgres_companies=len(pg_companies),
        graph_companies=len(graph_companies),
        postgres_transactions=len(pg_edges),
        graph_transactions=len(graph_edges),
        only_in_postgres=tuple(only_in_postgres),
        only_in_graph=tuple(only_in_graph),
    )
