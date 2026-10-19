"""The versioned invoice payload that gets signed.

Every field is normalized on the way in (see normalization.py), so the visible
invoice and the signed payload can be compared field by field. Money is an exact
Decimal with two places and is never a float.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.services.invoice_authentication import normalization as norm

PAYLOAD_VERSION = "verifigst.invoice.v1"


class InvoicePayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    payload_version: Literal["verifigst.invoice.v1"] = PAYLOAD_VERSION
    issuer_name: str
    issuer_domain: str
    invoice_number: str
    invoice_date: date
    buyer_name: str
    currency: str
    total_amount: Decimal
    tax_amount: Decimal
    payment_account: str | None = None
    document_reference: str | None = None

    @field_validator("issuer_name", "buyer_name", mode="before")
    @classmethod
    def _names(cls, value: object) -> str:
        return norm.normalize_name(value)

    @field_validator("issuer_domain", mode="before")
    @classmethod
    def _domain(cls, value: object) -> str:
        return norm.normalize_domain(value)

    @field_validator("invoice_number", mode="before")
    @classmethod
    def _invoice_number(cls, value: object) -> str:
        return norm.normalize_reference(value, max_length=64)

    @field_validator("document_reference", mode="before")
    @classmethod
    def _document_reference(cls, value: object) -> str | None:
        if value is None:
            return None
        return norm.normalize_reference(value, max_length=128)

    @field_validator("invoice_date", mode="before")
    @classmethod
    def _date(cls, value: object) -> date:
        return norm.parse_iso_date(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        return norm.normalize_currency(value)

    @field_validator("total_amount", "tax_amount", mode="before")
    @classmethod
    def _money(cls, value: object) -> Decimal:
        return norm.parse_money(value)

    @field_validator("payment_account", mode="before")
    @classmethod
    def _account(cls, value: object) -> str | None:
        if value is None:
            return None
        return norm.normalize_account(value)

    @model_validator(mode="after")
    def _check_amounts(self) -> "InvoicePayloadV1":
        if self.total_amount <= 0:
            raise ValueError("total_amount must be greater than zero")
        if self.tax_amount > self.total_amount:
            raise ValueError("tax_amount cannot exceed total_amount")
        return self

    def canonical_fields(self) -> dict[str, str | None]:
        """Every signed field as text (or null). This dictionary is what gets serialized."""
        return {
            "payload_version": self.payload_version,
            "issuer_name": self.issuer_name,
            "issuer_domain": self.issuer_domain,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat(),
            "buyer_name": self.buyer_name,
            "currency": self.currency,
            "total_amount": norm.format_money(self.total_amount),
            "tax_amount": norm.format_money(self.tax_amount),
            "payment_account": self.payment_account,
            "document_reference": self.document_reference,
        }
