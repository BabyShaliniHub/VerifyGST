"""A self-contained demonstration environment: one enrolled issuer and seven synthetic invoices.

It uses the same pipeline as real verification, with in-memory stand-ins for DNS, the
enrolment registry and the duplicate index. Signing keys are created when the server
starts, used only to sign the samples, and then discarded. They are never stored,
logged or returned.

Everything here is synthetic. Nothing describes a real company, invoice or account.
"""

from dataclasses import dataclass
from datetime import date

from app.services.invoice_authentication.comparison import COMPARED_FIELDS, VisibleField
from app.services.invoice_authentication.duplicates import InMemoryDuplicateIndex, SeenInvoice
from app.services.invoice_authentication.enrollment import (
    Enrollment,
    EnrollmentStatus,
    InMemoryEnrollmentRegistry,
)
from app.services.invoice_authentication.key_discovery import KeyDiscoveryService, StaticTxtResolver
from app.services.invoice_authentication.keys import generate_private_key, public_key_to_base64
from app.services.invoice_authentication.payload import InvoicePayloadV1
from app.services.invoice_authentication.pipeline import (
    InvoiceVerificationPipeline,
    SignedEnvelope,
    VerificationRequest,
)
from app.services.invoice_authentication.signing import sign_payload

DEMO_DOMAIN = "grove-chemicals.example"
DEMO_ISSUER = "Grove Chemicals"
DEMO_KEY_ID = "k1"

_BASE_FIELDS = {
    "issuer_name": DEMO_ISSUER,
    "issuer_domain": DEMO_DOMAIN,
    "invoice_number": "SYN-2026-0142",
    "invoice_date": "2026-10-02",
    "buyer_name": "Hazel Components",
    "currency": "INR",
    "total_amount": "640000.00",
    "tax_amount": "97627.12",
    "payment_account": "SYNTH000005521",
    "document_reference": "DOC-SYN-0142",
}


@dataclass(frozen=True)
class DemoSample:
    sample_id: str
    label: str
    request: VerificationRequest


@dataclass(frozen=True)
class DemoEnvironment:
    pipeline: InvoiceVerificationPipeline
    samples: tuple[DemoSample, ...]

    def sample(self, sample_id: str) -> DemoSample | None:
        for item in self.samples:
            if item.sample_id == sample_id:
                return item
        return None


def _visible(fields: dict, confidence: float = 0.98, **overrides) -> dict[str, VisibleField]:
    visible = {
        name: VisibleField(None if fields.get(name) is None else str(fields[name]), confidence)
        for name in COMPARED_FIELDS
    }
    for name, item in overrides.items():
        visible[name] = item if isinstance(item, VisibleField) else VisibleField(item, confidence)
    return visible


def _request(signer, fields: dict, visible: dict[str, VisibleField], key_id: str = DEMO_KEY_ID):
    signature = sign_payload(signer, InvoicePayloadV1(**fields))
    return VerificationRequest(visible, SignedEnvelope(dict(fields), signature, key_id), date.today())


def build_demo_environment() -> DemoEnvironment:
    published_key = generate_private_key()
    other_issuer_key = generate_private_key()
    impostor_key = generate_private_key()

    txt = f"v=verifigst1; kid={DEMO_KEY_ID}; k=ed25519; p={public_key_to_base64(published_key.public_key())}"
    resolver = StaticTxtResolver({"_verifigst." + DEMO_DOMAIN: [txt]})
    registry = InMemoryEnrollmentRegistry(
        [Enrollment(DEMO_DOMAIN, DEMO_ISSUER, EnrollmentStatus.ACTIVE, date(2026, 1, 5))]
    )
    index = InMemoryDuplicateIndex(
        [
            SeenInvoice("REC-D-001", DEMO_DOMAIN, "INV-D-202", "1" * 64),
            SeenInvoice("REC-D-002", DEMO_DOMAIN, "INV-D-202", "2" * 64),
        ]
    )
    pipeline = InvoiceVerificationPipeline(KeyDiscoveryService(resolver, registry), index)

    base = dict(_BASE_FIELDS)
    unenrolled = dict(
        base, issuer_name="Birch Metals", issuer_domain="birch-metals.example", invoice_number="SYN-2026-0201"
    )
    repeated = dict(base, invoice_number="INV-D-202")

    samples = (
        DemoSample("intact", "Intact invoice with a valid signature", _request(published_key, base, _visible(base))),
        DemoSample(
            "amount",
            "Visible amount differs from the signed amount",
            _request(published_key, base, _visible(base, total_amount="840000.00")),
        ),
        DemoSample(
            "account",
            "Payment account differs from the signed account",
            _request(published_key, base, _visible(base, payment_account="SYNTH000009083")),
        ),
        DemoSample(
            "bad-signature",
            "Signature does not verify",
            _request(impostor_key, base, _visible(base)),
        ),
        DemoSample(
            "unknown-key",
            "Issuer is not enrolled and no key is known",
            _request(other_issuer_key, unenrolled, _visible(unenrolled)),
        ),
        DemoSample(
            "low-confidence",
            "Low-confidence extraction",
            _request(
                published_key,
                base,
                _visible(
                    base,
                    invoice_number=VisibleField("SYN-2026-01?2", 0.58),
                    total_amount=VisibleField("6?0000.00", 0.61),
                ),
            ),
        ),
        DemoSample(
            "repeated",
            "Repeated invoice reference",
            _request(published_key, repeated, _visible(repeated)),
        ),
    )
    # The private keys go out of scope here. Nothing keeps them.
    return DemoEnvironment(pipeline, samples)
