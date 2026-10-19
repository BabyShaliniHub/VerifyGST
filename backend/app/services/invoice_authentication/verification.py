"""Verification side. It never signs and never needs a private key."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import signing_message

if TYPE_CHECKING:
    from .payload import InvoicePayloadV1

_SIGNATURE_LENGTH = 64


class SignatureStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    MALFORMED = "malformed"


@dataclass(frozen=True)
class SignatureCheck:
    status: SignatureStatus
    detail: str


def verify_payload_signature(
    public_key: Ed25519PublicKey,
    payload: InvoicePayloadV1,
    signature_b64: str,
) -> SignatureCheck:
    """Check one signature. A valid result means only that the signed payload verifies
    under this key. It does not show the goods or services were delivered, and it does
    not show who controls the key."""
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, TypeError):
        return SignatureCheck(SignatureStatus.MALFORMED, "The signature is not valid base64.")
    if len(signature) != _SIGNATURE_LENGTH:
        return SignatureCheck(SignatureStatus.MALFORMED, "The signature has the wrong length.")
    try:
        public_key.verify(signature, signing_message(payload.canonical_fields()))
    except InvalidSignature:
        return SignatureCheck(
            SignatureStatus.INVALID,
            "The signature does not verify for this payload and key.",
        )
    return SignatureCheck(SignatureStatus.VALID, "The signature verifies for the signed payload.")
