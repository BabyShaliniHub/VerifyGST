import hashlib
from datetime import date

import pytest

from app.services.invoice_authentication.canonical import signing_message
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
from app.services.invoice_authentication.results import CheckStatus, ProviderOutcome
from app.services.invoice_authentication.signing import sign_payload

# Synthetic values only.
FIELDS = {
    "issuer_name": "Grove Chemicals",
    "issuer_domain": "grove-chemicals.example",
    "invoice_number": "SYN-2026-0142",
    "invoice_date": "2026-10-02",
    "buyer_name": "Hazel Components",
    "currency": "INR",
    "total_amount": "640000.00",
    "tax_amount": "97627.12",
    "payment_account": "SYNTH000005521",
    "document_reference": "DOC-SYN-0142",
}
DOMAIN = FIELDS["issuer_domain"]
TODAY = date(2026, 10, 18)
S = CheckStatus


def key_record(key, kid="k1", **extra):
    fields = {"v": "verifigst1", "kid": kid, "k": "ed25519", "p": public_key_to_base64(key.public_key())}
    fields.update(extra)
    return "; ".join(f"{name}={value}" for name, value in fields.items())


def make_pipeline(
    key=None,
    enrolled=True,
    enrolled_name="Grove Chemicals",
    key_extra=None,
    duplicates=None,
    official=None,
    unavailable=False,
):
    texts = [] if key is None else [key_record(key, **(key_extra or {}))]
    resolver = StaticTxtResolver({"_verifigst." + DOMAIN: texts}, unavailable=unavailable)
    enrollments = [Enrollment(DOMAIN, enrolled_name, EnrollmentStatus.ACTIVE, date(2026, 1, 5))] if enrolled else []
    discovery = KeyDiscoveryService(resolver, InMemoryEnrollmentRegistry(enrollments))
    return InvoiceVerificationPipeline(discovery, duplicates or InMemoryDuplicateIndex(), official)


def visible_from(fields, confidence=0.98, **overrides):
    visible = {
        name: VisibleField(None if fields.get(name) is None else str(fields[name]), confidence)
        for name in COMPARED_FIELDS
    }
    for name, value in overrides.items():
        visible[name] = value if isinstance(value, VisibleField) else VisibleField(value, confidence)
    return visible


def signed_request(signer, fields=None, visible=None, key_id="k1", file_sha256=None):
    fields = fields or dict(FIELDS)
    payload = InvoicePayloadV1(**fields)
    envelope = SignedEnvelope(dict(fields), sign_payload(signer, payload), key_id)
    visible = visible_from(fields) if visible is None else visible
    return VerificationRequest(visible, envelope, TODAY, file_sha256)


def statuses(report):
    return {c.check_id: c.status for c in report.checks}


def field_statuses(report):
    return {f.field: f.status for f in report.fields}


def test_an_intact_invoice_passes_every_check_that_could_be_run():
    key = generate_private_key()
    report = make_pipeline(key).verify(signed_request(key))
    assert statuses(report) == {
        "field_extraction": S.PASSED,
        "issuer_key": S.PASSED,
        "signature": S.PASSED,
        "issuer_identity": S.PASSED,
        "payload_comparison": S.PASSED,
        "duplicate_reference": S.PASSED,
        "official_einvoice": S.NOT_CHECKED,
    }
    assert any("does not show that goods or services were delivered" in a for a in report.next_actions)


def test_a_changed_amount_is_flagged_even_though_the_signature_is_valid():
    key = generate_private_key()
    request = signed_request(key, visible=visible_from(FIELDS, total_amount="840000.00"))
    report = make_pipeline(key).verify(request)
    assert statuses(report)["signature"] is S.PASSED
    assert statuses(report)["payload_comparison"] is S.FAILED
    assert field_statuses(report)["total_amount"] is S.FAILED
    assert [n for n, s in field_statuses(report).items() if s is S.FAILED] == ["total_amount"]
    assert any("independent channel" in a for a in report.next_actions)


def test_a_changed_payment_account_is_flagged():
    key = generate_private_key()
    request = signed_request(key, visible=visible_from(FIELDS, payment_account="SYNTH000009083"))
    report = make_pipeline(key).verify(request)
    assert statuses(report)["payload_comparison"] is S.FAILED
    assert field_statuses(report)["payment_account"] is S.FAILED
    assert any("Do not release payment" in a for a in report.next_actions)


def test_a_signature_from_a_key_the_issuer_did_not_publish_fails():
    published, impostor = generate_private_key(), generate_private_key()
    report = make_pipeline(published).verify(signed_request(impostor))
    result = statuses(report)
    assert result["issuer_key"] is S.PASSED
    assert result["signature"] is S.FAILED
    assert result["issuer_identity"] is S.NOT_CHECKED
    assert result["payload_comparison"] is S.NOT_CHECKED
    assert all(s is S.NOT_CHECKED for s in field_statuses(report).values())
    assert any("Treat the document as unverified" in a for a in report.next_actions)


def test_an_issuer_that_is_not_enrolled_is_unknown_never_a_pass():
    key = generate_private_key()
    report = make_pipeline(key, enrolled=False).verify(signed_request(key))
    result = statuses(report)
    assert result["issuer_key"] is S.UNKNOWN
    assert result["signature"] is S.UNKNOWN
    assert result["issuer_identity"] is S.NOT_CHECKED
    assert result["payload_comparison"] is S.NOT_CHECKED


def test_an_issuer_with_no_published_key_is_unknown():
    report = make_pipeline(None).verify(signed_request(generate_private_key()))
    assert statuses(report)["issuer_key"] is S.UNKNOWN
    assert statuses(report)["signature"] is S.UNKNOWN


def test_a_failed_dns_lookup_is_unknown_never_a_pass():
    key = generate_private_key()
    report = make_pipeline(key, unavailable=True).verify(signed_request(key))
    assert statuses(report)["issuer_key"] is S.UNKNOWN
    assert statuses(report)["signature"] is S.UNKNOWN


def test_a_revoked_key_fails_the_key_check_and_the_signature_stays_unknown():
    key = generate_private_key()
    report = make_pipeline(key, key_extra={"rev": "2026-09-01"}).verify(signed_request(key))
    assert statuses(report)["issuer_key"] is S.FAILED
    assert statuses(report)["signature"] is S.UNKNOWN
    assert any("Ask the issuer which key is current" in a for a in report.next_actions)


def test_a_requested_key_id_that_is_not_published_is_unknown():
    key = generate_private_key()
    report = make_pipeline(key).verify(signed_request(key, key_id="missing"))
    assert statuses(report)["issuer_key"] is S.UNKNOWN


def test_low_confidence_extraction_asks_for_manual_review():
    key = generate_private_key()
    visible = visible_from(
        FIELDS,
        total_amount=VisibleField("6?0000.00", 0.61),
        invoice_number=VisibleField("SYN-2026-01?2", 0.58),
    )
    report = make_pipeline(key).verify(signed_request(key, visible=visible))
    result = statuses(report)
    assert result["field_extraction"] is S.MANUAL_REVIEW
    assert result["signature"] is S.PASSED
    assert result["payload_comparison"] is S.MANUAL_REVIEW
    assert field_statuses(report)["total_amount"] is S.MANUAL_REVIEW
    assert field_statuses(report)["invoice_number"] is S.MANUAL_REVIEW
    assert any("Review the document manually" in a for a in report.next_actions)


def test_an_empty_extraction_is_not_checked():
    key = generate_private_key()
    request = signed_request(key, visible={})
    report = make_pipeline(key).verify(request)
    assert statuses(report)["field_extraction"] is S.NOT_CHECKED
    assert statuses(report)["payload_comparison"] is S.MANUAL_REVIEW


def test_formatting_differences_do_not_cause_a_failure():
    key = generate_private_key()
    visible = visible_from(
        FIELDS, total_amount="640000", payment_account=" synth 0000-05521 ", issuer_name="GROVE CHEMICALS"
    )
    report = make_pipeline(key).verify(signed_request(key, visible=visible))
    assert statuses(report)["payload_comparison"] is S.PASSED


def test_a_thousands_separator_is_not_guessed_at():
    key = generate_private_key()
    report = make_pipeline(key).verify(signed_request(key, visible=visible_from(FIELDS, total_amount="640,000.00")))
    assert field_statuses(report)["total_amount"] is S.MANUAL_REVIEW


def test_an_account_printed_but_not_signed_is_a_failure():
    key = generate_private_key()
    fields = dict(FIELDS, payment_account=None)
    request = signed_request(key, fields=fields, visible=visible_from(fields, payment_account="SYNTH000005521"))
    report = make_pipeline(key).verify(request)
    assert field_statuses(report)["payment_account"] is S.FAILED


def test_a_signed_account_missing_from_the_document_needs_review():
    key = generate_private_key()
    report = make_pipeline(key).verify(signed_request(key, visible=visible_from(FIELDS, payment_account=None)))
    assert field_statuses(report)["payment_account"] is S.MANUAL_REVIEW
    assert statuses(report)["payload_comparison"] is S.MANUAL_REVIEW


def test_a_signed_issuer_name_that_differs_from_the_enrolled_name_fails():
    key = generate_private_key()
    report = make_pipeline(key, enrolled_name="Another Chemicals Ltd").verify(signed_request(key))
    assert statuses(report)["signature"] is S.PASSED
    assert statuses(report)["issuer_identity"] is S.FAILED
    assert any("enrolled issuer" in a for a in report.next_actions)


def test_a_malformed_signed_payload_fails_without_crashing():
    key = generate_private_key()
    envelope = SignedEnvelope({"issuer_domain": DOMAIN}, "AAAA", "k1")
    request = VerificationRequest(visible_from(FIELDS), envelope, TODAY)
    report = make_pipeline(key).verify(request)
    result = statuses(report)
    assert result["issuer_key"] is S.NOT_CHECKED
    assert result["signature"] is S.FAILED
    assert result["issuer_identity"] is S.NOT_CHECKED
    assert result["payload_comparison"] is S.NOT_CHECKED
    assert result["duplicate_reference"] is S.NOT_CHECKED


def test_a_payload_that_is_not_a_mapping_does_not_crash():
    key = generate_private_key()
    envelope = SignedEnvelope(["not", "a", "mapping"], "AAAA", None)
    request = VerificationRequest(visible_from(FIELDS), envelope, TODAY)
    assert statuses(make_pipeline(key).verify(request))["signature"] is S.FAILED


def test_a_document_without_signed_data_is_not_checked():
    key = generate_private_key()
    request = VerificationRequest(visible_from(FIELDS), None, TODAY, "f" * 64)
    result = statuses(make_pipeline(key).verify(request))
    assert result["issuer_key"] is S.NOT_CHECKED
    assert result["signature"] is S.NOT_CHECKED
    assert result["payload_comparison"] is S.NOT_CHECKED
    assert result["duplicate_reference"] is S.PASSED  # the file hash was still checked


def test_the_same_file_seen_before_needs_manual_review():
    key = generate_private_key()
    index = InMemoryDuplicateIndex([SeenInvoice("REC-1", file_sha256="a" * 64)])
    report = make_pipeline(key, duplicates=index).verify(signed_request(key, file_sha256="a" * 64))
    outcome = report.check("duplicate_reference")
    assert outcome.status is S.MANUAL_REVIEW
    assert "REC-1" in outcome.detail
    assert "this exact file" in outcome.detail
    assert any("file hashes" in a for a in report.next_actions)


def test_the_same_signed_content_seen_before_needs_manual_review():
    key = generate_private_key()
    payload = InvoicePayloadV1(**FIELDS)
    digest = hashlib.sha256(signing_message(payload.canonical_fields())).hexdigest()
    index = InMemoryDuplicateIndex([SeenInvoice("REC-2", DOMAIN, FIELDS["invoice_number"], digest)])
    outcome = make_pipeline(key, duplicates=index).verify(signed_request(key)).check("duplicate_reference")
    assert outcome.status is S.MANUAL_REVIEW
    assert "same signed content" in outcome.detail
    assert "different signed content" not in outcome.detail


def test_a_reused_invoice_number_with_different_content_needs_manual_review():
    key = generate_private_key()
    index = InMemoryDuplicateIndex([SeenInvoice("REC-3", DOMAIN, FIELDS["invoice_number"], "0" * 64)])
    outcome = make_pipeline(key, duplicates=index).verify(signed_request(key)).check("duplicate_reference")
    assert outcome.status is S.MANUAL_REVIEW
    assert "different signed content" in outcome.detail
    assert "not proof" in outcome.detail


def test_a_broken_duplicate_index_is_unknown_never_a_pass():
    class BrokenIndex:
        def find(self, **criteria):
            raise RuntimeError("database down")

    key = generate_private_key()
    outcome = make_pipeline(key, duplicates=BrokenIndex()).verify(signed_request(key)).check("duplicate_reference")
    assert outcome.status is S.UNKNOWN


def test_an_official_service_error_is_unknown_never_a_pass():
    class FailingOfficial:
        def check(self, irn):
            raise RuntimeError("service down")

    key = generate_private_key()
    report = make_pipeline(key, official=FailingOfficial()).verify(signed_request(key))
    assert report.check("official_einvoice").status is S.UNKNOWN


def test_an_official_service_result_is_passed_through_and_receives_the_reference():
    seen = []

    class FakeOfficial:
        def check(self, irn):
            seen.append(irn)
            return ProviderOutcome(S.PASSED, "Confirmed by the fake service.")

    key = generate_private_key()
    report = make_pipeline(key, official=FakeOfficial()).verify(signed_request(key))
    assert report.check("official_einvoice").status is S.PASSED
    assert seen == ["DOC-SYN-0142"]


def test_the_confidence_threshold_must_be_a_fraction():
    key = generate_private_key()
    discovery = make_pipeline(key)._discovery
    with pytest.raises(ValueError):
        InvoiceVerificationPipeline(discovery, InMemoryDuplicateIndex(), confidence_threshold=1.5)
