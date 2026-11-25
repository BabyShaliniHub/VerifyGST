"""Find cycles in the graph and explain each one with facts read from PostgreSQL.

PostgreSQL is authoritative for companies and transactions. The graph only says which loops exist.

Findings are sorted by review priority, but only within the cycles the search returned. When the
search is truncated, the cycles it kept are the first ones in id order, not the highest priority,
so a truncated list must be read as incomplete.
"""

from dataclasses import dataclass

from neo4j import Driver
from sqlalchemy import Connection, text

from app.analysis.findings import Finding, TransactionFact, build_finding
from app.graph.cycles import find_cycles
from app.graph.sync import to_minor_units

_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class FindingSet:
    findings: tuple[Finding, ...]
    truncated: bool  # True when the cycle search hit its result limit
    min_length: int
    max_length: int


def read_transaction_facts(connection: Connection, transaction_ids: set[str]) -> dict[str, TransactionFact]:
    if not transaction_ids:
        return {}
    rows = connection.execute(
        text(
            "SELECT id, seller_company_id, buyer_company_id, invoice_reference, amount, currency, "
            "occurred_on, evidence_level FROM transactions WHERE id::text = ANY(:ids)"
        ),
        {"ids": sorted(transaction_ids)},
    )
    return {
        str(r.id): TransactionFact(
            id=str(r.id),
            seller_id=str(r.seller_company_id),
            buyer_id=str(r.buyer_company_id),
            invoice_reference=r.invoice_reference,
            amount_minor=to_minor_units(r.amount),
            currency=r.currency,
            occurred_on=r.occurred_on,
            evidence_level=r.evidence_level,
        )
        for r in rows
    }


def read_company_names(connection: Connection, company_ids: set[str]) -> dict[str, str]:
    if not company_ids:
        return {}
    rows = connection.execute(
        text("SELECT id, name FROM companies WHERE id::text = ANY(:ids)"),
        {"ids": sorted(company_ids)},
    )
    return {str(r.id): r.name for r in rows}


def analyse_cycles(
    connection: Connection,
    driver: Driver,
    *,
    min_length: int = 3,
    max_length: int = 6,
    max_results: int = 50,
    timeout_seconds: float = 5.0,
) -> FindingSet:
    search = find_cycles(
        driver,
        min_length=min_length,
        max_length=max_length,
        max_results=max_results,
        timeout_seconds=timeout_seconds,
    )
    transaction_ids = {i for cycle in search.cycles for i in cycle.transaction_ids}
    company_ids = {i for cycle in search.cycles for i in cycle.company_ids}
    facts = read_transaction_facts(connection, transaction_ids)
    names = read_company_names(connection, company_ids)

    findings = [build_finding(cycle, facts, names) for cycle in search.cycles]
    findings.sort(key=lambda f: (_PRIORITY_RANK[f.priority], f.length, f.company_ids))
    return FindingSet(tuple(findings), search.truncated, search.min_length, search.max_length)
