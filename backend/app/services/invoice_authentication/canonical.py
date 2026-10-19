"""Canonical byte serialization used for signing and verifying.

Signing and verification both call signing_message(), so they always use
identical bytes. Only text and null values are allowed, which avoids the number
formatting ambiguities of JSON.
"""

import json
from collections.abc import Mapping

# Domain separation: a signature made for an invoice payload cannot be replayed
# as a signature over some other kind of message.
SIGNING_CONTEXT = b"verifigst.invoice.v1\x00"


def canonical_json_bytes(fields: Mapping[str, str | None]) -> bytes:
    for key, value in fields.items():
        if not isinstance(key, str) or not (value is None or isinstance(value, str)):
            raise TypeError("canonical fields must be text or null")
    text = json.dumps(
        dict(fields),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return text.encode("ascii")


def signing_message(fields: Mapping[str, str | None]) -> bytes:
    return SIGNING_CONTEXT + canonical_json_bytes(fields)
