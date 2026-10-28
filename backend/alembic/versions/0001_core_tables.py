"""Core tables: companies, invoices, transactions, verification results and the audit log.

Revision ID: 0001
Revises:
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "companies",
        _id(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("domain", name=op.f("uq_companies_domain")),
        sa.UniqueConstraint("gstin", name=op.f("uq_companies_gstin")),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 200", name=op.f("ck_companies_name_length")),
        sa.CheckConstraint("domain IS NULL OR domain = lower(domain)", name=op.f("ck_companies_domain_lowercase")),
        sa.CheckConstraint("gstin IS NULL OR char_length(gstin) = 15", name=op.f("ck_companies_gstin_length")),
    )

    op.create_table(
        "invoices",
        _id(),
        sa.Column("issuer_company_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_company_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_account", sa.Text(), nullable=True),
        sa.Column("document_reference", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invoices")),
        sa.ForeignKeyConstraint(
            ["issuer_company_id"],
            ["companies.id"],
            name=op.f("fk_invoices_issuer_company_id_companies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_company_id"],
            ["companies.id"],
            name=op.f("fk_invoices_buyer_company_id_companies"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("char_length(invoice_number) BETWEEN 1 AND 64", name=op.f("ck_invoices_number_length")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_invoices_currency_format")),
        sa.CheckConstraint("total_amount > 0", name=op.f("ck_invoices_total_positive")),
        sa.CheckConstraint("tax_amount >= 0 AND tax_amount <= total_amount", name=op.f("ck_invoices_tax_range")),
        sa.CheckConstraint(
            "file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_invoices_file_hash_format")
        ),
        sa.CheckConstraint(
            "payload_sha256 IS NULL OR payload_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_invoices_payload_hash_format"),
        ),
        sa.CheckConstraint("issuer_company_id <> buyer_company_id", name=op.f("ck_invoices_parties_differ")),
    )
    op.create_index(op.f("ix_invoices_issuer_number"), "invoices", ["issuer_company_id", "invoice_number"])
    op.create_index(op.f("ix_invoices_file_sha256"), "invoices", ["file_sha256"])
    op.create_index(op.f("ix_invoices_payload_sha256"), "invoices", ["payload_sha256"])

    op.create_table(
        "transactions",
        _id(),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("seller_company_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_company_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_reference", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("evidence_level", sa.Text(), server_default=sa.text("'missing'"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name=op.f("fk_transactions_invoice_id_invoices"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["seller_company_id"],
            ["companies.id"],
            name=op.f("fk_transactions_seller_company_id_companies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_company_id"],
            ["companies.id"],
            name=op.f("fk_transactions_buyer_company_id_companies"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_transactions_amount_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_transactions_currency_format")),
        sa.CheckConstraint("seller_company_id <> buyer_company_id", name=op.f("ck_transactions_parties_differ")),
        sa.CheckConstraint(
            "evidence_level IN ('complete', 'partial', 'missing')",
            name=op.f("ck_transactions_evidence_level_valid"),
        ),
    )
    op.create_index(op.f("ix_transactions_seller"), "transactions", ["seller_company_id"])
    op.create_index(op.f("ix_transactions_buyer"), "transactions", ["buyer_company_id"])
    op.create_index(op.f("ix_transactions_occurred_on"), "transactions", ["occurred_on"])
    op.create_index(op.f("ix_transactions_invoice"), "transactions", ["invoice_id"])

    op.create_table(
        "verification_runs",
        _id(),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=True),
        sa.Column("verification_date", sa.Date(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_runs")),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_verification_runs_invoice_id_invoices"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_verification_runs_file_hash_format"),
        ),
    )
    op.create_index(op.f("ix_verification_runs_invoice"), "verification_runs", ["invoice_id"])
    op.create_index(op.f("ix_verification_runs_created_at"), "verification_runs", ["created_at"])

    op.create_table(
        "verification_checks",
        _id(),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("check_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_checks")),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["verification_runs.id"],
            name=op.f("fk_verification_checks_run_id_verification_runs"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("run_id", "check_id", name=op.f("uq_verification_checks_run_check")),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'unknown', 'not_checked', 'manual_review')",
            name=op.f("ck_verification_checks_status_valid"),
        ),
    )

    op.create_table(
        "audit_events",
        _id(),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor", sa.Text(), server_default=sa.text("'system'"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.CheckConstraint("char_length(action) BETWEEN 1 AND 100", name=op.f("ck_audit_events_action_length")),
        sa.CheckConstraint(
            "char_length(entity_type) BETWEEN 1 AND 100", name=op.f("ck_audit_events_entity_type_length")
        ),
        sa.CheckConstraint("jsonb_typeof(details) = 'object'", name=op.f("ck_audit_events_details_is_object")),
    )
    op.create_index(op.f("ix_audit_events_entity"), "audit_events", ["entity_type", "entity_id"])
    op.create_index(op.f("ix_audit_events_occurred_at"), "audit_events", ["occurred_at"])

    # The audit log is append-only: the database itself refuses to change or remove a row.
    op.execute(
        """
        CREATE FUNCTION audit_events_block_changes() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_row_changes
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_block_changes();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_truncate
        BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION audit_events_block_changes();
        """
    )


def downgrade() -> None:
    op.drop_table("audit_events")  # also removes its triggers
    op.execute("DROP FUNCTION audit_events_block_changes()")
    op.drop_table("verification_checks")
    op.drop_table("verification_runs")
    op.drop_table("transactions")
    op.drop_table("invoices")
    op.drop_table("companies")
