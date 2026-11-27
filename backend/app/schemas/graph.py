from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: str
    name: str
    domain: str | None
    is_synthetic: bool


class TransactionOut(BaseModel):
    id: str
    seller_id: str
    buyer_id: str
    invoice_reference: str | None
    amount: Decimal  # sent as an exact decimal string such as "4800000.00", never as a float
    currency: str
    occurred_on: date
    evidence_level: str  # complete, partial or missing
    note: str | None
    is_synthetic: bool


class GraphTruncation(BaseModel):
    companies: bool
    transactions: bool


class GraphResponse(BaseModel):
    companies: list[CompanyOut]
    transactions: list[TransactionOut]
    truncated: GraphTruncation  # true means more rows exist than the limit allowed
    contains_synthetic_data: bool
