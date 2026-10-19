import base64

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.services.invoice_authentication.canonical import (
    SIGNING_CONTEXT,
    canonical_json_bytes,
    signing_message,
)
from app.services.invoice_authentication.keys import (
    generate_private_key,
    public_key_from_base64,
    public_key_to_base64,
)
from app.services.invoice_authentication.payload import InvoicePayloadV1
from app.services.invoice_authentication.signing import sign_payload
from app.services.invoice_authentication.verification import (
    SignatureStatus,
    verify_payload_signature,
)

# This seed exists only for the golden test below. It never signs anything real.
TEST_ONLY_SEED = bytes(range(32))
EXPECTED_PUBLIC_KEY = "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg="
EXPECTED_SIGNATURE = (
    "9dkR5TuVs1CmOhUx5RjQVHHJWNGlWMyzTZB/shgFaAcYsCWNnifA1pqgidkbI7TwVoR+oGeKqR5jBAMzKuW+Dg=="
)


def build(fields, **changes):
    return InvoicePayloadV1(**{**fields, **changes})


def test_valid_signature_verifies(payload, private_key):
    signature = sign_payload(private_key, payload)
    result = verify_payload_signature(private_key.public_key(), payload, signature)
    assert result.status is SignatureStatus.VALID


@pytest.mark.parametrize(
    "field, value",
    [
        ("total_amount", "840000.00"),
        ("payment_account", "SYNTH000009083"),
        ("payment_account", None),
        ("invoice_number", "SYN-2026-0143"),
        ("buyer_name", "Someone Else"),
        ("issuer_name", "Other Chemicals"),
        ("issuer_domain", "other.example"),
        ("tax_amount", "1.00"),
        ("currency", "USD"),
        ("invoice_date", "2026-10-03"),
        ("document_reference", "DOC-OTHER"),
        ("document_reference", None),
    ],
)
def test_changing_any_signed_field_makes_verification_fail(valid_fields, private_key, field, value):
    signature = sign_payload(private_key, build(valid_fields))
    tampered = build(valid_fields, **{field: value})
    result = verify_payload_signature(private_key.public_key(), tampered, signature)
    assert result.status is SignatureStatus.INVALID


def test_wrong_public_key_fails(payload, private_key):
    signature = sign_payload(private_key, payload)
    other_key = generate_private_key().public_key()
    assert verify_payload_signature(other_key, payload, signature).status is SignatureStatus.INVALID


def test_a_flipped_signature_bit_fails(payload, private_key):
    raw = bytearray(base64.b64decode(sign_payload(private_key, payload)))
    raw[0] ^= 1
    tampered = base64.b64encode(bytes(raw)).decode("ascii")
    result = verify_payload_signature(private_key.public_key(), payload, tampered)
    assert result.status is SignatureStatus.INVALID


def test_equivalent_formatting_produces_the_same_signed_bytes(valid_fields, private_key):
    signature = sign_payload(private_key, build(valid_fields))
    messy = build(
        valid_fields,
        total_amount="640000",
        payment_account=" synth 0000-05521 ",
        issuer_domain="GROVE-CHEMICALS.example",
        buyer_name=" Hazel  Components",
    )
    result = verify_payload_signature(private_key.public_key(), messy, signature)
    assert result.status is SignatureStatus.VALID


def test_malformed_signatures_never_crash_and_never_pass(payload, private_key):
    good = sign_payload(private_key, payload)
    candidates = [
        "",
        "not base64!!",
        base64.b64encode(b"x" * 10).decode("ascii"),
        "A" * 88,
        good[:-4],
        good + "==",
        good[:10] + "\n" + good[10:],
        None,
        123,
    ]
    for candidate in candidates:
        result = verify_payload_signature(private_key.public_key(), payload, candidate)
        assert result.status is SignatureStatus.MALFORMED, candidate


def test_signing_uses_a_context_prefix(payload, private_key):
    assert signing_message(payload.canonical_fields()).startswith(SIGNING_CONTEXT)
    # A signature over the bare canonical bytes (no context) must not verify.
    bare = private_key.sign(canonical_json_bytes(payload.canonical_fields()))
    bare_b64 = base64.b64encode(bare).decode("ascii")
    result = verify_payload_signature(private_key.public_key(), payload, bare_b64)
    assert result.status is SignatureStatus.INVALID


def test_public_key_round_trip(private_key):
    text = public_key_to_base64(private_key.public_key())
    assert public_key_to_base64(public_key_from_base64(text)) == text


@pytest.mark.parametrize(
    "bad",
    ["", "!!!", base64.b64encode(b"x" * 31).decode("ascii"), base64.b64encode(b"x" * 33).decode("ascii"), None, 5],
)
def test_bad_public_keys_are_rejected(bad):
    with pytest.raises(ValueError):
        public_key_from_base64(bad)


def test_golden_signature_and_public_key(payload):
    # Ed25519 signatures are deterministic, so a fixed seed gives a fixed signature.
    key = Ed25519PrivateKey.from_private_bytes(TEST_ONLY_SEED)
    assert public_key_to_base64(key.public_key()) == EXPECTED_PUBLIC_KEY
    assert sign_payload(key, payload) == EXPECTED_SIGNATURE
