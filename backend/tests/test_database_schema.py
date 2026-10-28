import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db import models  # noqa: F401  (registers the tables)
from app.db.base import Base
from app.db.models import Company
from app.db.session import IntegrationState, check_database, create_db_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "companies",
    "invoices",
    "transactions",
    "verification_runs",
    "verification_checks",
    "audit_events",
}


@pytest.fixture
def connection():
    """A connection inside a transaction that is always rolled back, so tests leave no rows."""
    if check_database().state is not IntegrationState.CONNECTED:
        pytest.skip("PostgreSQL is not available. Start it with: docker compose up -d")
    engine = create_db_engine(get_settings())
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            yield conn
        finally:
            transaction.rollback()
    engine.dispose()


def rejected(conn, action, error=IntegrityError):
    """Run an action that the database must refuse, without ending the test transaction."""
    with pytest.raises(error):
        with conn.begin_nested():
            action()


def add_company(conn, name="Demo Company", domain=None, gstin=None):
    return conn.execute(
        text(
            "INSERT INTO companies (name, domain, gstin, is_synthetic) "
            "VALUES (:name, :domain, :gstin, true) RETURNING id"
        ),
        {"name": name, "domain": domain, "gstin": gstin},
    ).scalar_one()


def add_invoice(conn, issuer, buyer, **overrides):
    values = {
        "issuer": issuer,
        "buyer": buyer,
        "invoice_number": "SYN-1",
        "invoice_date": date(2026, 10, 2),
        "currency": "INR",
        "total_amount": Decimal("1000.00"),
        "tax_amount": Decimal("150.00"),
        "file_sha256": None,
        "payload_sha256": None,
    }
    values.update(overrides)
    return conn.execute(
        text(
            "INSERT INTO invoices (issuer_company_id, buyer_company_id, invoice_number, invoice_date, "
            "currency, total_amount, tax_amount, file_sha256, payload_sha256, is_synthetic) "
            "VALUES (:issuer, :buyer, :invoice_number, :invoice_date, :currency, :total_amount, "
            ":tax_amount, :file_sha256, :payload_sha256, true) RETURNING id"
        ),
        values,
    ).scalar_one()


def add_transaction(conn, seller, buyer, **overrides):
    values = {
        "seller": seller,
        "buyer": buyer,
        "amount": Decimal("500.00"),
        "currency": "INR",
        "occurred_on": date(2026, 10, 3),
        "evidence_level": "partial",
    }
    values.update(overrides)
    return conn.execute(
        text(
            "INSERT INTO transactions (seller_company_id, buyer_company_id, amount, currency, "
            "occurred_on, evidence_level, is_synthetic) "
            "VALUES (:seller, :buyer, :amount, :currency, :occurred_on, :evidence_level, true) RETURNING id"
        ),
        values,
    ).scalar_one()


def add_run(conn):
    return conn.execute(
        text(
            "INSERT INTO verification_runs (verification_date, engine_version) "
            "VALUES (:day, :version) RETURNING id"
        ),
        {"day": date(2026, 10, 18), "version": "0.1.0"},
    ).scalar_one()


def add_check(conn, run_id, check_id="signature", status="passed"):
    conn.execute(
        text(
            "INSERT INTO verification_checks (run_id, position, check_id, label, status, detail) "
            "VALUES (:run, 1, :check_id, 'Signature verification', :status, 'detail')"
        ),
        {"run": run_id, "check_id": check_id, "status": status},
    )


def add_audit_event(conn):
    return conn.execute(
        text("INSERT INTO audit_events (action, entity_type) VALUES ('test.action', 'test') RETURNING id")
    ).scalar_one()


def test_the_database_is_at_the_latest_migration(connection):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    head = ScriptDirectory.from_config(config).get_current_head()
    current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert current == head


def test_every_expected_table_exists(connection):
    rows = connection.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    ).scalars()
    assert EXPECTED_TABLES <= set(rows)


def test_the_models_and_the_database_have_the_same_columns(connection):
    for name, table in Base.metadata.tables.items():
        database_columns = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :name"
                ),
                {"name": name},
            ).scalars()
        )
        assert {column.name for column in table.columns} == database_columns, name


def test_the_orm_models_can_write_and_read_rows(connection):
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        company = Company(name="ORM Company", is_synthetic=True)
        session.add(company)
        session.flush()
        assert isinstance(company.id, uuid.UUID)
        assert session.get(Company, company.id).name == "ORM Company"
    finally:
        session.close()


def test_a_valid_company_is_stored_with_defaults(connection):
    company_id = add_company(connection, domain="grove-chemicals.example")
    row = connection.execute(
        text("SELECT is_synthetic, created_at IS NOT NULL AS stamped FROM companies WHERE id = :id"),
        {"id": company_id},
    ).one()
    assert row.is_synthetic is True
    assert row.stamped is True


def test_company_rules_are_enforced_by_the_database(connection):
    add_company(connection, domain="taken.example", gstin="A" * 15)
    rejected(connection, lambda: add_company(connection, name=""))
    rejected(connection, lambda: add_company(connection, name="x" * 201))
    rejected(connection, lambda: add_company(connection, domain="Upper-Case.example"))
    rejected(connection, lambda: add_company(connection, gstin="TOO-SHORT"))
    rejected(connection, lambda: add_company(connection, domain="taken.example"))
    rejected(connection, lambda: add_company(connection, gstin="A" * 15))


def test_a_valid_invoice_is_stored(connection):
    issuer, buyer = add_company(connection, "Issuer"), add_company(connection, "Buyer")
    assert add_invoice(connection, issuer, buyer) is not None


def test_invoice_rules_are_enforced_by_the_database(connection):
    issuer, buyer = add_company(connection, "Issuer"), add_company(connection, "Buyer")
    bad_values = [
        {"total_amount": Decimal("0.00"), "tax_amount": Decimal("0.00")},
        {"tax_amount": Decimal("1000.01")},
        {"tax_amount": Decimal("-0.01")},
        {"currency": "inr"},
        {"currency": "IN"},
        {"invoice_number": ""},
        {"file_sha256": "xyz"},
        {"payload_sha256": "A" * 64},
    ]
    for overrides in bad_values:
        rejected(connection, lambda o=overrides: add_invoice(connection, issuer, buyer, **o))
    rejected(connection, lambda: add_invoice(connection, issuer, issuer))


def test_an_invoice_must_point_at_real_companies(connection):
    real = add_company(connection)
    rejected(connection, lambda: add_invoice(connection, real, uuid.uuid4()))
    rejected(connection, lambda: add_invoice(connection, uuid.uuid4(), real))


def test_a_company_with_invoices_cannot_be_deleted(connection):
    issuer, buyer = add_company(connection, "Issuer"), add_company(connection, "Buyer")
    add_invoice(connection, issuer, buyer)
    rejected(connection, lambda: connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": issuer}))


def test_repeated_invoice_references_are_stored_not_blocked(connection):
    issuer, buyer = add_company(connection, "Issuer"), add_company(connection, "Buyer")
    add_invoice(connection, issuer, buyer, invoice_number="INV-D-202")
    add_invoice(connection, issuer, buyer, invoice_number="INV-D-202")
    count = connection.execute(
        text("SELECT count(*) FROM invoices WHERE invoice_number = 'INV-D-202'")
    ).scalar_one()
    assert count == 2


def test_transaction_rules_are_enforced_by_the_database(connection):
    seller, buyer = add_company(connection, "Seller"), add_company(connection, "Buyer")
    assert add_transaction(connection, seller, buyer) is not None
    rejected(connection, lambda: add_transaction(connection, seller, seller))
    rejected(connection, lambda: add_transaction(connection, seller, buyer, amount=Decimal("0.00")))
    rejected(connection, lambda: add_transaction(connection, seller, buyer, currency="RS"))
    rejected(connection, lambda: add_transaction(connection, seller, buyer, evidence_level="great"))
    rejected(connection, lambda: add_transaction(connection, seller, uuid.uuid4()))


def test_a_transaction_without_evidence_defaults_to_missing(connection):
    seller, buyer = add_company(connection, "Seller"), add_company(connection, "Buyer")
    transaction_id = connection.execute(
        text(
            "INSERT INTO transactions (seller_company_id, buyer_company_id, amount, currency, occurred_on) "
            "VALUES (:s, :b, 10, 'INR', '2026-10-03') RETURNING id"
        ),
        {"s": seller, "b": buyer},
    ).scalar_one()
    level = connection.execute(
        text("SELECT evidence_level FROM transactions WHERE id = :id"), {"id": transaction_id}
    ).scalar_one()
    assert level == "missing"


def test_verification_checks_belong_to_a_run_and_follow_the_five_states(connection):
    run_id = add_run(connection)
    for status in ("passed", "failed", "unknown", "not_checked", "manual_review"):
        add_check(connection, run_id, check_id=f"check_{status}", status=status)
    rejected(connection, lambda: add_check(connection, run_id, check_id="another", status="verified"))
    rejected(connection, lambda: add_check(connection, run_id, check_id="check_passed"))
    rejected(connection, lambda: add_check(connection, uuid.uuid4()))


def test_deleting_a_run_removes_its_checks(connection):
    run_id = add_run(connection)
    add_check(connection, run_id)
    connection.execute(text("DELETE FROM verification_runs WHERE id = :id"), {"id": run_id})
    left = connection.execute(
        text("SELECT count(*) FROM verification_checks WHERE run_id = :id"), {"id": run_id}
    ).scalar_one()
    assert left == 0


def test_an_audit_event_is_stored_with_defaults(connection):
    event_id = add_audit_event(connection)
    row = connection.execute(
        text("SELECT actor, details, occurred_at IS NOT NULL AS stamped FROM audit_events WHERE id = :id"),
        {"id": event_id},
    ).one()
    assert row.actor == "system"
    assert row.details == {}
    assert row.stamped is True


def test_audit_events_cannot_be_changed_deleted_or_truncated(connection):
    event_id = add_audit_event(connection)
    rejected(
        connection,
        lambda: connection.execute(
            text("UPDATE audit_events SET action = 'changed' WHERE id = :id"), {"id": event_id}
        ),
        DBAPIError,
    )
    rejected(
        connection,
        lambda: connection.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id}),
        DBAPIError,
    )
    rejected(connection, lambda: connection.execute(text("TRUNCATE audit_events")), DBAPIError)
    still_there = connection.execute(
        text("SELECT count(*) FROM audit_events WHERE id = :id"), {"id": event_id}
    ).scalar_one()
    assert still_there == 1


def test_audit_event_rules_are_enforced_by_the_database(connection):
    rejected(connection, lambda: connection.execute(text("INSERT INTO audit_events (action, entity_type) VALUES ('', 'x')")))
    rejected(
        connection,
        lambda: connection.execute(
            text("INSERT INTO audit_events (action, entity_type, details) VALUES ('a', 'x', CAST('[]' AS jsonb))")
        ),
    )
