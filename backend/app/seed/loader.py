"""Load the synthetic demonstration data into PostgreSQL.

Idempotent: every row has a stable id and an insert that conflicts is skipped, so running the
seed again changes nothing. The caller owns the transaction.
"""

from dataclasses import dataclass

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import AuditEvent, Company, Transaction
from app.seed.demo_data import COMPANIES, TRANSACTIONS, stable_id


@dataclass(frozen=True)
class SeedResult:
    companies_inserted: int
    transactions_inserted: int


def seed_postgres(connection: Connection, *, audit: bool = True) -> SeedResult:
    company_rows = [
        {
            "id": stable_id("company", c.key),
            "name": c.name,
            "domain": c.domain,
            "is_synthetic": True,
        }
        for c in COMPANIES
    ]
    transaction_rows = [
        {
            "id": stable_id("transaction", t.key),
            "seller_company_id": stable_id("company", t.seller_key),
            "buyer_company_id": stable_id("company", t.buyer_key),
            "invoice_reference": t.invoice_reference,
            "amount": t.amount,
            "currency": "INR",
            "occurred_on": t.occurred_on,
            "evidence_level": t.evidence_level,
            "note": t.note,
            "is_synthetic": True,
        }
        for t in TRANSACTIONS
    ]

    # RETURNING gives back only the rows that were really inserted. The driver's rowcount is
    # -1 for a multi-row insert, so it cannot be used to count them.
    companies = len(
        connection.execute(
            pg_insert(Company.__table__)
            .values(company_rows)
            .on_conflict_do_nothing()
            .returning(Company.__table__.c.id)
        ).all()
    )
    transactions = len(
        connection.execute(
            pg_insert(Transaction.__table__)
            .values(transaction_rows)
            .on_conflict_do_nothing()
            .returning(Transaction.__table__.c.id)
        ).all()
    )

    if audit:
        connection.execute(
            pg_insert(AuditEvent.__table__).values(
                actor="seed-script",
                action="seed.demo_data",
                entity_type="seed",
                details={"companies_inserted": companies, "transactions_inserted": transactions},
            )
        )
    return SeedResult(companies, transactions)
