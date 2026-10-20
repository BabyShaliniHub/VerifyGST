"""The verification pipeline: runs every check and reports each result separately.

There is deliberately no overall verdict. Each check answers one question:

  field_extraction     could the visible fields be read reliably?
  issuer_key           does an enrolled issuer publish a usable key?
  signature            does the signed payload verify under that key?
  issuer_identity      does the signed issuer name match the enrolled name?
  payload_comparison   do the visible fields match the signed payload?
  duplicate_reference  has this file, signed content or invoice number been seen before?
  official_einvoice    would an authorized e-invoice service confirm it? (not connected)

Nothing is treated as a pass unless it was actually checked and succeeded. Missing data,
unreachable services and unknown keys become Unknown, Not checked or Manual review.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from . import normalization as norm
from .canonical import signing_message
from .comparison import FIELD_LABELS, VisibleField, compare_fields, roll_up
from .duplicates import DuplicateIndex
from .key_discovery import DiscoveryStatus, KeyDiscoveryResult, KeyDiscoveryService
from .results import (
    CheckOutcome,
    CheckStatus,
    FieldComparison,
    ProviderOutcome,
    VerificationReport,
)
from .verification import SignatureStatus, verify_payload_signature

CHECK_EXTRACTION = "field_extraction"
CHECK_KEY = "issuer_key"
CHECK_SIGNATURE = "signature"
CHECK_IDENTITY = "issuer_identity"
CHECK_COMPARISON = "payload_comparison"
CHECK_DUPLICATE = "duplicate_reference"
CHECK_OFFICIAL = "official_einvoice"

_NO_ENVELOPE = "No signed payload was found on the document."

_KEY_STATUS_MAP = {
    DiscoveryStatus.TRUSTED: CheckStatus.PASSED,
    DiscoveryStatus.NOT_ENROLLED: CheckStatus.UNKNOWN,
    DiscoveryStatus.ENROLMENT_PENDING: CheckStatus.UNKNOWN,
    DiscoveryStatus.NO_KEY: CheckStatus.UNKNOWN,
    DiscoveryStatus.INVALID_DOMAIN: CheckStatus.UNKNOWN,
    DiscoveryStatus.LOOKUP_UNAVAILABLE: CheckStatus.UNKNOWN,
    DiscoveryStatus.ENROLMENT_SUSPENDED: CheckStatus.FAILED,
    DiscoveryStatus.KEY_REVOKED: CheckStatus.FAILED,
    DiscoveryStatus.KEY_EXPIRED: CheckStatus.FAILED,
    DiscoveryStatus.KEY_NOT_YET_VALID: CheckStatus.FAILED,
}


class OfficialVerifier(Protocol):
    """Connects an authorized e-invoice verification service (IRN and signed QR)."""

    def check(self, irn: str | None) -> ProviderOutcome: ...


class NotConfiguredOfficialVerifier:
    def check(self, irn: str | None) -> ProviderOutcome:
        return ProviderOutcome(
            CheckStatus.NOT_CHECKED,
            "No authorized e-invoice verification service is connected. "
            "VerifiGST does not replace the official process.",
        )


@dataclass(frozen=True)
class SignedEnvelope:
    """The untrusted signed data found on the document (for example, from a QR code)."""

    payload: Mapping[str, Any]
    signature_b64: str
    key_id: str | None = None


@dataclass(frozen=True)
class VerificationRequest:
    visible: Mapping[str, VisibleField]
    envelope: SignedEnvelope | None
    verification_date: date
    file_sha256: str | None = None


class InvoiceVerificationPipeline:
    def __init__(
        self,
        key_discovery: KeyDiscoveryService,
        duplicates: DuplicateIndex,
        official: OfficialVerifier | None = None,
        *,
        confidence_threshold: float = 0.85,
        payload_parser: Callable[[Mapping[str, Any]], Any] | None = None,
    ) -> None:
        if not (0.0 <= confidence_threshold <= 1.0):
            raise ValueError("confidence_threshold must be between 0 and 1")
        if payload_parser is None:
            from .payload import InvoicePayloadV1

            payload_parser = InvoicePayloadV1.model_validate
        self._discovery = key_discovery
        self._duplicates = duplicates
        self._official = official or NotConfiguredOfficialVerifier()
        self._threshold = confidence_threshold
        self._parse = payload_parser

    def verify(self, request: VerificationRequest) -> VerificationReport:
        envelope = request.envelope
        payload: Any = None
        malformed = False
        if envelope is not None:
            try:
                payload = self._parse(dict(envelope.payload))
            except Exception:  # untrusted input must never crash the pipeline
                malformed = True

        discovery: KeyDiscoveryResult | None = None
        if payload is not None:
            discovery = self._discovery.discover(
                payload.issuer_domain, request.verification_date, envelope.key_id
            )

        extraction = self._extraction(request.visible)
        key = self._key(envelope, malformed, discovery)
        signature = self._signature(envelope, payload, malformed, discovery)
        signature_ok = signature.status is CheckStatus.PASSED
        identity = self._identity(payload, signature_ok, discovery)
        comparison, fields = self._comparison(request.visible, payload, signature_ok)
        duplicate = self._duplicate(request, payload)
        official = self._official_check(payload)

        checks = (extraction, key, signature, identity, comparison, duplicate, official)
        return VerificationReport(checks, fields, self._next_actions(checks, fields))

    # -- individual checks -------------------------------------------------

    def _extraction(self, visible: Mapping[str, VisibleField]) -> CheckOutcome:
        label = "Field extraction"
        if not visible:
            return CheckOutcome(CHECK_EXTRACTION, label, CheckStatus.NOT_CHECKED, "No fields were extracted from the document.")
        problems = []
        for field, text in FIELD_LABELS.items():
            item = visible.get(field)
            if item is None or item.value is None:
                if field != "payment_account":
                    problems.append(f"the {text} was not found")
            elif item.confidence < self._threshold:
                problems.append(f"the {text} was read with low confidence ({round(item.confidence * 100)} percent)")
        if problems:
            detail = "Manual review is needed: " + "; ".join(problems) + "."
            return CheckOutcome(CHECK_EXTRACTION, label, CheckStatus.MANUAL_REVIEW, detail)
        detail = f"All fields were read with at least {round(self._threshold * 100)} percent confidence."
        return CheckOutcome(CHECK_EXTRACTION, label, CheckStatus.PASSED, detail)

    def _key(self, envelope, malformed: bool, discovery: KeyDiscoveryResult | None) -> CheckOutcome:
        label = "Issuer public key"
        if envelope is None:
            return CheckOutcome(CHECK_KEY, label, CheckStatus.NOT_CHECKED, _NO_ENVELOPE)
        if malformed or discovery is None:
            return CheckOutcome(
                CHECK_KEY,
                label,
                CheckStatus.NOT_CHECKED,
                "The signed payload is malformed or unsupported, so the issuer could not be identified.",
            )
        return CheckOutcome(CHECK_KEY, label, _KEY_STATUS_MAP[discovery.status], discovery.detail)

    def _signature(self, envelope, payload, malformed: bool, discovery: KeyDiscoveryResult | None) -> CheckOutcome:
        label = "Signature verification"
        if envelope is None:
            return CheckOutcome(CHECK_SIGNATURE, label, CheckStatus.NOT_CHECKED, _NO_ENVELOPE)
        if malformed:
            return CheckOutcome(
                CHECK_SIGNATURE,
                label,
                CheckStatus.FAILED,
                "The signed payload is malformed or unsupported, so it cannot be verified.",
            )
        if discovery is None or not discovery.is_trusted:
            return CheckOutcome(
                CHECK_SIGNATURE,
                label,
                CheckStatus.UNKNOWN,
                "The signature cannot be checked without a trusted issuer key.",
            )
        results = [
            (k, verify_payload_signature(k.public_key, payload, envelope.signature_b64))
            for k in discovery.keys
        ]
        for key, result in results:
            if result.status is SignatureStatus.VALID:
                return CheckOutcome(
                    CHECK_SIGNATURE,
                    label,
                    CheckStatus.PASSED,
                    f"The signature verifies for the signed payload (key {key.key_id}).",
                )
        for _, result in results:
            if result.status is SignatureStatus.MALFORMED:
                return CheckOutcome(CHECK_SIGNATURE, label, CheckStatus.FAILED, result.detail)
        return CheckOutcome(
            CHECK_SIGNATURE,
            label,
            CheckStatus.FAILED,
            "The signature does not verify under any key this issuer has published.",
        )

    def _identity(self, payload, signature_ok: bool, discovery: KeyDiscoveryResult | None) -> CheckOutcome:
        label = "Issuer identity"
        if payload is None:
            return CheckOutcome(CHECK_IDENTITY, label, CheckStatus.NOT_CHECKED, "There is no readable signed payload to check.")
        if not signature_ok or discovery is None or discovery.enrollment is None:
            return CheckOutcome(CHECK_IDENTITY, label, CheckStatus.NOT_CHECKED, "Not run, because the signature did not verify.")
        try:
            enrolled = norm.normalize_name(discovery.enrollment.issuer_name).casefold()
        except ValueError:
            return CheckOutcome(CHECK_IDENTITY, label, CheckStatus.UNKNOWN, "The registered issuer name is not usable.")
        if enrolled == payload.issuer_name.casefold():
            return CheckOutcome(CHECK_IDENTITY, label, CheckStatus.PASSED, "The signed issuer name matches the enrolled issuer.")
        return CheckOutcome(
            CHECK_IDENTITY, label, CheckStatus.FAILED, "The signed issuer name differs from the enrolled issuer name."
        )

    def _comparison(self, visible, payload, signature_ok: bool) -> tuple[CheckOutcome, tuple[FieldComparison, ...]]:
        label = "Signed payload comparison"
        if payload is None or not signature_ok:
            unchecked = tuple(
                FieldComparison(field, item.value if (item := visible.get(field)) else None, None, CheckStatus.NOT_CHECKED)
                for field in FIELD_LABELS
            )
            detail = "Not run, because the signed payload is not verified."
            return CheckOutcome(CHECK_COMPARISON, label, CheckStatus.NOT_CHECKED, detail), unchecked

        fields = compare_fields(visible, payload.canonical_fields(), self._threshold)
        failed = [FIELD_LABELS[c.field] for c in fields if c.status is CheckStatus.FAILED]
        review = [FIELD_LABELS[c.field] for c in fields if c.status is CheckStatus.MANUAL_REVIEW]
        if failed:
            detail = f"Differs from the signed payload: {', '.join(failed)}."
            if review:
                detail += f" Could not be compared reliably: {', '.join(review)}."
        elif review:
            detail = f"Could not be compared reliably: {', '.join(review)}."
        else:
            detail = "All compared fields match the signed payload."
        return CheckOutcome(CHECK_COMPARISON, label, roll_up(fields), detail), fields

    def _duplicate(self, request: VerificationRequest, payload) -> CheckOutcome:
        label = "Duplicate reference check"
        payload_hash = domain = number = None
        if payload is not None:
            payload_hash = hashlib.sha256(signing_message(payload.canonical_fields())).hexdigest()
            domain, number = payload.issuer_domain, payload.invoice_number
        if request.file_sha256 is None and payload is None:
            return CheckOutcome(
                CHECK_DUPLICATE, label, CheckStatus.NOT_CHECKED, "There is no file hash or readable signed payload to check against."
            )
        try:
            matches = self._duplicates.find(
                file_sha256=request.file_sha256,
                payload_sha256=payload_hash,
                issuer_domain=domain,
                invoice_number=number,
            )
        except Exception:
            return CheckOutcome(CHECK_DUPLICATE, label, CheckStatus.UNKNOWN, "The duplicate index could not be reached. This is not a pass.")
        if not matches:
            return CheckOutcome(
                CHECK_DUPLICATE, label, CheckStatus.PASSED, "No earlier record uses this file, signed content or invoice reference."
            )
        reasons = []
        if request.file_sha256 and any(m.file_sha256 == request.file_sha256 for m in matches):
            reasons.append("this exact file was seen before")
        if payload_hash and any(m.payload_sha256 == payload_hash for m in matches):
            reasons.append("the same signed content was seen before")
        if domain and number and any(
            m.issuer_domain == domain and m.invoice_number == number and m.payload_sha256 != payload_hash
            for m in matches
        ):
            reasons.append("the same issuer and invoice number appeared with different signed content")
        ids = ", ".join(sorted(m.record_id for m in matches))
        detail = (
            f"Earlier record(s) {ids}: {'; '.join(reasons)}. "
            "A repeated document is not proof of a duplicate payment or of fraud."
        )
        return CheckOutcome(CHECK_DUPLICATE, label, CheckStatus.MANUAL_REVIEW, detail)

    def _official_check(self, payload) -> CheckOutcome:
        label = "IRN and QR verification (official)"
        irn = payload.document_reference if payload is not None else None
        try:
            result = self._official.check(irn)
        except Exception:
            return CheckOutcome(CHECK_OFFICIAL, label, CheckStatus.UNKNOWN, "The verification service returned an error. This is not a pass.")
        return CheckOutcome(CHECK_OFFICIAL, label, result.status, result.detail)

    # -- guidance ----------------------------------------------------------

    @staticmethod
    def _next_actions(checks: tuple[CheckOutcome, ...], fields: tuple[FieldComparison, ...]) -> tuple[str, ...]:
        by_id = {c.check_id: c for c in checks}
        actions: list[str] = []

        def add(text: str) -> None:
            if text not in actions:
                actions.append(text)

        failed_fields = {f.field for f in fields if f.status is CheckStatus.FAILED}
        if "payment_account" in failed_fields:
            add("Do not release payment. Confirm the payment account with the issuer through an independent channel.")
        if failed_fields - {"payment_account"}:
            add("Do not rely on the visible values. Obtain the original invoice from the issuer through an independent channel.")
        if by_id[CHECK_SIGNATURE].status is CheckStatus.FAILED:
            add("Treat the document as unverified. Ask the issuer to confirm or re-issue the invoice.")
        if by_id[CHECK_KEY].status is CheckStatus.UNKNOWN:
            add("Check whether the issuer is enrolled and ask them to publish or confirm their verification key.")
        if by_id[CHECK_KEY].status is CheckStatus.FAILED:
            add("Ask the issuer which key is current. Do not rely on a signature made with this key.")
        if by_id[CHECK_IDENTITY].status is CheckStatus.FAILED:
            add("Investigate why the signed issuer name differs from the enrolled issuer before relying on the document.")
        if by_id[CHECK_EXTRACTION].status is CheckStatus.MANUAL_REVIEW or any(
            f.status is CheckStatus.MANUAL_REVIEW for f in fields
        ):
            add("Review the document manually and correct the extracted fields, then run the checks again.")
        if by_id[CHECK_DUPLICATE].status is CheckStatus.MANUAL_REVIEW:
            add("Compare the documents behind the repeated reference, including file hashes, before drawing any conclusion.")
        if by_id[CHECK_SIGNATURE].status is CheckStatus.PASSED:
            add("A valid signature does not show that goods or services were delivered. Compare the invoice with delivery and payment records.")
        return tuple(actions)
