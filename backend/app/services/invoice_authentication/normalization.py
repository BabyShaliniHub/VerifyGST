"""Pure normalization helpers for invoice fields.

No third-party imports. Each function returns the normalized value or raises
ValueError with a safe message (the message never echoes the input).
"""

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal

_CENT = Decimal("0.01")
_MAX_AMOUNT = Decimal("10000000000000")  # exclusive upper bound: 10 to the power 13
_MONEY_RE = re.compile(r"\d{1,13}(\.\d{1,2})?")
_DOMAIN_LABEL_RE = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_REFERENCE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9/._-]*")
_CURRENCY_RE = re.compile(r"[A-Z]{3}")
_ACCOUNT_RE = re.compile(r"[A-Z0-9]{4,34}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _require_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("must be text")
    return value


def normalize_name(value: object, *, max_length: int = 200) -> str:
    """Unicode NFC, collapse whitespace, reject control and invisible characters."""
    text = unicodedata.normalize("NFC", _require_text(value))
    text = " ".join(text.split())
    if not text:
        raise ValueError("must not be empty")
    if len(text) > max_length:
        raise ValueError("is too long")
    if any(unicodedata.category(ch).startswith("C") for ch in text):
        raise ValueError("contains control or invisible characters")
    return text


def normalize_domain(value: object) -> str:
    """Lowercase ASCII domain name with at least two valid labels."""
    text = _require_text(value).strip().lower()
    if text.endswith("."):
        text = text[:-1]
    if not text.isascii():
        raise ValueError("must be ASCII (use the punycode form)")
    if len(text) > 253:
        raise ValueError("is too long")
    labels = text.split(".")
    if len(labels) < 2 or not all(_DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
        raise ValueError("is not a valid domain name")
    return text


def normalize_reference(value: object, *, max_length: int = 64) -> str:
    """Invoice numbers and document references: letters, digits and / . _ - only."""
    text = _require_text(value).strip()
    if not text or len(text) > max_length or not _REFERENCE_RE.fullmatch(text):
        raise ValueError("is not a valid reference")
    return text


def normalize_currency(value: object) -> str:
    text = _require_text(value).strip().upper()
    if not _CURRENCY_RE.fullmatch(text):
        raise ValueError("must be a three-letter currency code")
    return text


def normalize_account(value: object) -> str:
    """Remove spaces and hyphens, uppercase, then require 4 to 34 letters or digits."""
    text = re.sub(r"[\s-]", "", _require_text(value)).upper()
    if not _ACCOUNT_RE.fullmatch(text):
        raise ValueError("is not a valid account identifier")
    return text


def parse_iso_date(value: object) -> date:
    """Accept a date object or a YYYY-MM-DD string. Datetimes and numbers are rejected."""
    if isinstance(value, datetime):
        raise ValueError("must be a date, not a date and time")
    if isinstance(value, date):
        return value
    text = _require_text(value).strip()
    if not _DATE_RE.fullmatch(text):
        raise ValueError("must look like YYYY-MM-DD")
    return date.fromisoformat(text)


def parse_money(value: object) -> Decimal:
    """Exact two-decimal amount. Floats are rejected so rounding never happens silently."""
    if isinstance(value, (bool, float)):
        raise ValueError("must be a string, integer or Decimal, not a float")
    if isinstance(value, str):
        text = value.strip()
        if not _MONEY_RE.fullmatch(text):
            raise ValueError("must look like 1234.50")
        amount = Decimal(text)
    elif isinstance(value, (int, Decimal)):
        amount = Decimal(value)
    else:
        raise ValueError("must be a string, integer or Decimal")
    if not amount.is_finite():
        raise ValueError("must be a finite number")
    if amount < 0:
        raise ValueError("must not be negative")
    if amount >= _MAX_AMOUNT:
        raise ValueError("is too large")
    if amount != amount.quantize(_CENT):
        raise ValueError("can have at most two decimal places")
    return amount.quantize(_CENT)


def format_money(amount: Decimal) -> str:
    """Canonical text for an amount: always exactly two decimals, never an exponent."""
    return format(amount.quantize(_CENT), "f")
