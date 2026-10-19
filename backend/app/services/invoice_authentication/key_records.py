"""Strict parser for the DNS TXT record that publishes an issuer's verification key.

A record is one line of fields separated by semicolons:

    v=verifigst1; kid=2026a; k=ed25519; p=<base64 of the 32-byte public key>; nb=2026-01-01; na=2027-01-01

Required: v, kid, k, p.  Optional: nb (not before), na (not after), rev (revoked on).
Anything that does not match this format exactly is rejected. Text that merely
exists in DNS is never treated as a key.
"""

import re
from dataclasses import dataclass
from datetime import date

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .keys import public_key_from_base64
from .normalization import parse_iso_date

RECORD_VERSION = "verifigst1"
MAX_RECORD_LENGTH = 512

_KEY_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}")
_ALLOWED_FIELDS = {"v", "kid", "k", "p", "nb", "na", "rev"}


class KeyRecordError(ValueError):
    """The TXT text is not a valid VerifiGST key record."""


@dataclass(frozen=True)
class KeyRecord:
    key_id: str
    public_key: Ed25519PublicKey
    not_before: date | None
    not_after: date | None
    revoked_on: date | None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_on is not None


def _optional_date(fields: dict[str, str], name: str) -> date | None:
    if name not in fields:
        return None
    try:
        return parse_iso_date(fields[name])
    except ValueError:
        raise KeyRecordError(f"field {name} is not a valid date") from None


def parse_key_record(text: object) -> KeyRecord:
    if not isinstance(text, str):
        raise KeyRecordError("record is not text")
    if len(text) > MAX_RECORD_LENGTH:
        raise KeyRecordError("record is too long")
    if not text.isascii():
        raise KeyRecordError("record contains non-ASCII characters")

    fields: dict[str, str] = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        name, separator, value = part.partition("=")
        name = name.strip().lower()
        value = value.strip()
        if not separator or name not in _ALLOWED_FIELDS or not value:
            raise KeyRecordError("record has an unknown or empty field")
        if name in fields:
            raise KeyRecordError("record repeats a field")
        fields[name] = value

    if fields.get("v", "").lower() != RECORD_VERSION:
        raise KeyRecordError("record version is missing or unsupported")
    key_id = fields.get("kid", "")
    if not _KEY_ID_RE.fullmatch(key_id):
        raise KeyRecordError("record key id is missing or invalid")
    if fields.get("k", "").lower() != "ed25519":
        raise KeyRecordError("record algorithm is missing or unsupported")
    try:
        public_key = public_key_from_base64(fields.get("p", ""))
    except ValueError:
        raise KeyRecordError("record public key is missing or invalid") from None

    not_before = _optional_date(fields, "nb")
    not_after = _optional_date(fields, "na")
    revoked_on = _optional_date(fields, "rev")
    if not_before and not_after and not_before > not_after:
        raise KeyRecordError("record validity window is reversed")

    return KeyRecord(key_id, public_key, not_before, not_after, revoked_on)
