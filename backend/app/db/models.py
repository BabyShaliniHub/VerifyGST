"""Relational models. PostgreSQL is the authoritative store for business records.

The database itself enforces the rules (check constraints, foreign keys, unique keys), so a
mistake in application code cannot store an impossible row. Money is NUMERIC(15,2).
Rows with is_synthetic = true are demonstration data and describe no real business.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _id_column():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at_column():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 200", name="ck_companies_name_length"),
        CheckConstraint("domain IS NULL OR domain = lower(domain)", name="ck_companies_domain_lowercase"),
        CheckConstraint("gstin IS NULL OR char_length(gstin) = 15", name="ck_companies_gstin_length"),
    )

    id: Mapped[uuid.UUID] = _id_column()
    name: Mapped[str] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text, unique=True)
    gstin: Mapped[str | None] = mapped_column(String(15), unique=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("char_length(invoice_number) BETWEEN 1 AND 64", name="ck_invoices_number_length"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_invoices_currency_format"),
        CheckConstraint("total_amount > 0", name="ck_invoices_total_positive"),
        CheckConstraint("tax_amount >= 0 AND tax_amount <= total_amount", name="ck_invoices_tax_range"),
        CheckConstraint("file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'", name="ck_invoices_file_hash_format"),
        CheckConstraint(
            "payload_sha256 IS NULL OR payload_sha256 ~ '^[0-9a-f]{64}$'", name="ck_invoices_payload_hash_format"
        ),
        CheckConstraint("issuer_company_id <> buyer_company_id", name="ck_invoices_parties_differ"),
        Index("ix_invoices_issuer_number", "issuer_company_id", "invoice_number"),
        Index("ix_invoices_file_sha256", "file_sha256"),
        Index("ix_invoices_payload_sha256", "payload_sha256"),
    )

    id: Mapped[uuid.UUID] = _id_column()
    issuer_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    buyer_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    invoice_number: Mapped[str] = mapped_column(Text)
    invoice_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    payment_account: Mapped[str | None] = mapped_column(Text)  # sensitive: never log or export
    document_reference: Mapped[str | None] = mapped_column(Text)
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    payload_sha256: Mapped[str | None] = mapped_column(String(64))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created_at_column()


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_transactions_currency_format"),
        CheckConstraint("seller_company_id <> buyer_company_id", name="ck_transactions_parties_differ"),
        CheckConstraint(
            "evidence_level IN ('complete', 'partial', 'missing')", name="ck_transactions_evidence_level_valid"
        ),
        Index("ix_transactions_seller", "seller_company_id"),
        Index("ix_transactions_buyer", "buyer_company_id"),
        Index("ix_transactions_occurred_on", "occurred_on"),
        Index("ix_transactions_invoice", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = _id_column()
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"))
    seller_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    buyer_company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    invoice_reference: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3))
    occurred_on: Mapped[date] = mapped_column(Date)
    evidence_level: Mapped[str] = mapped_column(Text, server_default=text("'missing'"))
    note: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = _created_at_column()


class VerificationRun(Base):
    __tablename__ = "verification_runs"
    __table_args__ = (
        CheckConstraint(
            "file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'", name="ck_verification_runs_file_hash_format"
        ),
        Index("ix_verification_runs_invoice", "invoice_id"),
        Index("ix_verification_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = _id_column()
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    verification_date: Mapped[date] = mapped_column(Date)
    engine_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _created_at_column()


class VerificationCheck(Base):
    __tablename__ = "verification_checks"
    __table_args__ = (
        UniqueConstraint("run_id", "check_id", name="uq_verification_checks_run_check"),
        CheckConstraint(
            "status IN ('passed', 'failed', 'unknown', 'not_checked', 'manual_review')",
            name="ck_verification_checks_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = _id_column()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verification_runs.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    check_id: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text)


class AuditEvent(Base):
    """Append-only. A database trigger rejects every UPDATE, DELETE and TRUNCATE."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("char_length(action) BETWEEN 1 AND 100", name="ck_audit_events_action_length"),
        CheckConstraint("char_length(entity_type) BETWEEN 1 AND 100", name="ck_audit_events_entity_type_length"),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="ck_audit_events_details_is_object"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = _id_column()
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(Text, server_default=text("'system'"))
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))  # never put secrets here
