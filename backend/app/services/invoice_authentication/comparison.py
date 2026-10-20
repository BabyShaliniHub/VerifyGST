"""Compare what is visible on the invoice with what was signed, field by field.

Visible text is normalized with the same rules as the signed payload, so harmless
formatting differences (spacing, letter case in codes, a leading zero in the amount)
do not matter. A match is positive evidence. A mismatch read with high confidence is a
failure. A mismatch read with low confidence, or text that cannot be read at all, needs
manual review rather than a verdict.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from . import normalization as norm
from .results import CheckStatus, FieldComparison

COMPARED_FIELDS = (
    "invoice_number",
    "invoice_date",
    "issuer_name",
    "buyer_name",
    "currency",
    "total_amount",
    "tax_amount",
    "payment_account",
)

FIELD_LABELS = {
    "invoice_number": "invoice number",
    "invoice_date": "invoice date",
    "issuer_name": "issuer",
    "buyer_name": "buyer",
    "currency": "currency",
    "total_amount": "amount",
    "tax_amount": "tax amount",
    "payment_account": "payment account",
}

_NAME_FIELDS = {"issuer_name", "buyer_name"}

_NORMALIZERS: dict[str, Callable[[str], str]] = {
    "invoice_number": lambda v: norm.normalize_reference(v, max_length=64),
    "invoice_date": lambda v: norm.parse_iso_date(v).isoformat(),
    "issuer_name": norm.normalize_name,
    "buyer_name": norm.normalize_name,
    "currency": norm.normalize_currency,
    "total_amount": lambda v: norm.format_money(norm.parse_money(v)),
    "tax_amount": lambda v: norm.format_money(norm.parse_money(v)),
    "payment_account": norm.normalize_account,
}


@dataclass(frozen=True)
class VisibleField:
    """One value read from the document, with the reader's confidence from 0 to 1."""

    value: str | None
    confidence: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")


def _same(field: str, visible: str, signed: str) -> bool:
    if field in _NAME_FIELDS:
        return visible.casefold() == signed.casefold()
    return visible == signed


def compare_fields(
    visible: Mapping[str, VisibleField],
    signed: Mapping[str, str | None],
    threshold: float,
) -> tuple[FieldComparison, ...]:
    results: list[FieldComparison] = []
    for field in COMPARED_FIELDS:
        signed_value = signed.get(field)
        item = visible.get(field)

        if item is None or item.value is None or not item.value.strip():
            if field == "payment_account" and signed_value is None:
                status = CheckStatus.PASSED  # no account on the document and none signed
            else:
                status = CheckStatus.MANUAL_REVIEW  # not found, so it cannot be compared
            results.append(FieldComparison(field, None, signed_value, status))
            continue

        try:
            visible_value = _NORMALIZERS[field](item.value)
        except ValueError:
            results.append(FieldComparison(field, item.value, signed_value, CheckStatus.MANUAL_REVIEW))
            continue

        confident = item.confidence >= threshold
        if signed_value is None:
            # Only the payment account can be unsigned. An account printed on the document but
            # not covered by the signature is a real risk, so it is a failure when read clearly.
            status = CheckStatus.FAILED if confident else CheckStatus.MANUAL_REVIEW
        elif _same(field, visible_value, signed_value):
            status = CheckStatus.PASSED
        else:
            status = CheckStatus.FAILED if confident else CheckStatus.MANUAL_REVIEW
        results.append(FieldComparison(field, visible_value, signed_value, status))
    return tuple(results)


def roll_up(comparisons: tuple[FieldComparison, ...]) -> CheckStatus:
    statuses = {c.status for c in comparisons}
    if CheckStatus.FAILED in statuses:
        return CheckStatus.FAILED
    if CheckStatus.MANUAL_REVIEW in statuses:
        return CheckStatus.MANUAL_REVIEW
    return CheckStatus.PASSED
