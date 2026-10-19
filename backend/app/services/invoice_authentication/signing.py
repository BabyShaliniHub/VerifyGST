"""Signing side. Used by issuers and by tests. Verification lives in verification.py."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canonical import signing_message

if TYPE_CHECKING:
    from .payload import InvoicePayloadV1


def sign_payload(private_key: Ed25519PrivateKey, payload: InvoicePayloadV1) -> str:
    """Return the Ed25519 signature over the payload as standard base64 text."""
    signature = private_key.sign(signing_message(payload.canonical_fields()))
    return base64.b64encode(signature).decode("ascii")
