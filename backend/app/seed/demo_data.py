"""Synthetic demonstration data: the same companies and transactions as the Network Explorer demo.

Everything here is invented. No company, invoice or amount describes a real business.
Ids are derived from stable keys (uuid5), so loading the seed twice never creates duplicates
and the same record always has the same id.

The graph contains two directed cycles of three companies:
  C1 -> C2 -> C3 -> C1  (transactions T1, T2, T3), with complete evidence
  C4 -> C5 -> C6 -> C4  (transactions T4, T5, T6), with evidence gaps and a repeated reference
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

# A fixed namespace for the derived ids. Changing it would change every seeded id.
NAMESPACE = uuid.UUID("0c2f6a52-5b6e-4c4c-9d0e-2f2a7a1d9b11")


def stable_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


@dataclass(frozen=True)
class SeedCompany:
    key: str
    name: str
    domain: str


@dataclass(frozen=True)
class SeedTransaction:
    key: str
    seller_key: str
    buyer_key: str
    invoice_reference: str
    amount: Decimal
    occurred_on: date
    evidence_level: str
    note: str | None = None


COMPANIES = (
    SeedCompany("C1", "Alder Traders", "alder-traders.example"),
    SeedCompany("C2", "Birch Metals", "birch-metals.example"),
    SeedCompany("C3", "Cedar Logistics", "cedar-logistics.example"),
    SeedCompany("C4", "Dune Textiles", "dune-textiles.example"),
    SeedCompany("C5", "Elm Packaging", "elm-packaging.example"),
    SeedCompany("C6", "Fern Agro", "fern-agro.example"),
    SeedCompany("C7", "Grove Chemicals", "grove-chemicals.example"),
    SeedCompany("C8", "Hazel Components", "hazel-components.example"),
)

TRANSACTIONS = (
    SeedTransaction("T1", "C1", "C2", "INV-D-101", Decimal("1250000.00"), date(2026, 7, 5), "complete"),
    SeedTransaction("T2", "C2", "C3", "INV-D-102", Decimal("1180000.00"), date(2026, 7, 19), "complete"),
    SeedTransaction("T3", "C3", "C1", "INV-D-103", Decimal("1300000.00"), date(2026, 8, 2), "complete"),
    SeedTransaction("T4", "C4", "C5", "INV-D-201", Decimal("4800000.00"), date(2026, 9, 10), "missing"),
    SeedTransaction("T5", "C5", "C6", "INV-D-202", Decimal("4790000.00"), date(2026, 9, 11), "missing"),
    SeedTransaction("T6", "C6", "C4", "INV-D-202", Decimal("4780000.00"), date(2026, 9, 12), "partial"),
    SeedTransaction("T7", "C3", "C7", "INV-D-104", Decimal("640000.00"), date(2026, 8, 14), "complete"),
    SeedTransaction(
        "T8",
        "C7",
        "C8",
        "INV-D-105",
        Decimal("610000.00"),
        date(2026, 8, 28),
        "partial",
        note=(
            "The linked invoice total is INR 640,000 but the transaction records INR 610,000. "
            "This could be a partial payment or a correction."
        ),
    ),
    SeedTransaction("T9", "C8", "C4", "INV-D-106", Decimal("520000.00"), date(2026, 9, 5), "partial"),
)
