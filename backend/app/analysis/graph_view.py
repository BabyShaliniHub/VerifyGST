"""Read the companies and transactions that the Network Explorer draws. PostgreSQL is the source."""

from sqlalchemy import Connection, text

from app.schemas.graph import CompanyOut, GraphResponse, GraphTruncation, TransactionOut


def read_graph_view(connection: Connection, limit: int) -> GraphResponse:
    # One extra row tells us whether the limit cut anything off.
    company_rows = connection.execute(
        text("SELECT id, name, domain, is_synthetic FROM companies ORDER BY name, id LIMIT :limit"),
        {"limit": limit + 1},
    ).all()
    transaction_rows = connection.execute(
        text(
            "SELECT id, seller_company_id, buyer_company_id, invoice_reference, amount, currency, "
            "occurred_on, evidence_level, note, is_synthetic "
            "FROM transactions ORDER BY occurred_on, id LIMIT :limit"
        ),
        {"limit": limit + 1},
    ).all()

    companies = [
        CompanyOut(id=str(r.id), name=r.name, domain=r.domain, is_synthetic=r.is_synthetic)
        for r in company_rows[:limit]
    ]
    transactions = [
        TransactionOut(
            id=str(r.id),
            seller_id=str(r.seller_company_id),
            buyer_id=str(r.buyer_company_id),
            invoice_reference=r.invoice_reference,
            amount=r.amount,
            currency=r.currency,
            occurred_on=r.occurred_on,
            evidence_level=r.evidence_level,
            note=r.note,
            is_synthetic=r.is_synthetic,
        )
        for r in transaction_rows[:limit]
    ]
    return GraphResponse(
        companies=companies,
        transactions=transactions,
        truncated=GraphTruncation(
            companies=len(company_rows) > limit, transactions=len(transaction_rows) > limit
        ),
        contains_synthetic_data=any(c.is_synthetic for c in companies)
        or any(t.is_synthetic for t in transactions),
    )
