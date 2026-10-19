"""Ed25519 public-key helpers. Private keys are never stored or serialized here."""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def generate_private_key() -> Ed25519PrivateKey:
    """For tests and local demonstrations. Production keys are created and held by issuers."""
    return Ed25519PrivateKey.generate()


def public_key_to_base64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def public_key_from_base64(value: str) -> Ed25519PublicKey:
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ValueError("public key is not valid base64") from None
    if len(raw) != 32:
        raise ValueError("public key must be exactly 32 bytes")
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError:
        raise ValueError("public key bytes are not valid") from None
