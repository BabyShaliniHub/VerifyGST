import pytest

from app.services.invoice_authentication.comparison import (
    COMPARED_FIELDS,
    VisibleField,
    compare_fields,
    roll_up,
)
from app.services.invoice_authentication.results import CheckStatus

SIGNED = {
    "invoice_number": "SYN-2026-0142",
    "invoice_date": "2026-10-02",
    "issuer_name": "Grove Chemicals",
    "buyer_name": "Hazel Components",
    "currency": "INR",
    "total_amount": "640000.00",
    "tax_amount": "97627.12",
    "payment_account": "SYNTH000005521",
}
THRESHOLD = 0.85


def visible(confidence=0.98, **overrides):
    values = dict(SIGNED)
    values.update(overrides)
    return {
        name: VisibleField(values[name], confidence) for name in COMPARED_FIELDS if name in values
    }


def status_of(results, field):
    return {r.field: r.status for r in results}[field]


def test_matching_fields_pass():
    results = compare_fields(visible(), SIGNED, THRESHOLD)
    assert all(r.status is CheckStatus.PASSED for r in results)
    assert roll_up(results) is CheckStatus.PASSED


def test_harmless_formatting_differences_still_match():
    results = compare_fields(
        visible(total_amount="640000", payment_account=" synth 0000-05521 ", currency="inr"),
        SIGNED,
        THRESHOLD,
    )
    assert roll_up(results) is CheckStatus.PASSED


def test_names_ignore_letter_case():
    results = compare_fields(visible(issuer_name="GROVE CHEMICALS"), SIGNED, THRESHOLD)
    assert status_of(results, "issuer_name") is CheckStatus.PASSED


def test_a_clear_mismatch_fails():
    results = compare_fields(visible(total_amount="840000.00"), SIGNED, THRESHOLD)
    assert status_of(results, "total_amount") is CheckStatus.FAILED
    assert roll_up(results) is CheckStatus.FAILED


def test_a_mismatch_read_with_low_confidence_needs_review_not_a_verdict():
    low = visible()
    low["total_amount"] = VisibleField("840000.00", 0.60)
    results = compare_fields(low, SIGNED, THRESHOLD)
    assert status_of(results, "total_amount") is CheckStatus.MANUAL_REVIEW
    assert roll_up(results) is CheckStatus.MANUAL_REVIEW


def test_a_match_read_with_low_confidence_still_counts_as_a_match():
    low = visible()
    low["total_amount"] = VisibleField("640000.00", 0.60)
    results = compare_fields(low, SIGNED, THRESHOLD)
    assert status_of(results, "total_amount") is CheckStatus.PASSED


def test_text_that_cannot_be_read_needs_review():
    for field, text in [
        ("total_amount", "640,000.00"),
        ("total_amount", "abc"),
        ("invoice_date", "02/10/2026"),
        ("invoice_number", "has space"),
    ]:
        results = compare_fields(visible(**{field: text}), SIGNED, THRESHOLD)
        assert status_of(results, field) is CheckStatus.MANUAL_REVIEW, (field, text)


def test_a_field_missing_from_the_document_needs_review():
    partial = visible()
    del partial["buyer_name"]
    results = compare_fields(partial, SIGNED, THRESHOLD)
    assert status_of(results, "buyer_name") is CheckStatus.MANUAL_REVIEW


def test_no_account_anywhere_is_fine_but_a_missing_account_that_was_signed_needs_review():
    signed_without_account = dict(SIGNED, payment_account=None)
    none_on_document = visible()
    del none_on_document["payment_account"]
    results = compare_fields(none_on_document, signed_without_account, THRESHOLD)
    assert status_of(results, "payment_account") is CheckStatus.PASSED

    results = compare_fields(none_on_document, SIGNED, THRESHOLD)
    assert status_of(results, "payment_account") is CheckStatus.MANUAL_REVIEW


def test_an_account_printed_on_the_document_but_not_signed_is_a_failure():
    signed_without_account = dict(SIGNED, payment_account=None)
    results = compare_fields(visible(), signed_without_account, THRESHOLD)
    assert status_of(results, "payment_account") is CheckStatus.FAILED

    shaky = visible()
    shaky["payment_account"] = VisibleField(SIGNED["payment_account"], 0.5)
    results = compare_fields(shaky, signed_without_account, THRESHOLD)
    assert status_of(results, "payment_account") is CheckStatus.MANUAL_REVIEW


def test_a_failure_outranks_a_review():
    mixed = visible(total_amount="840000.00")
    mixed["buyer_name"] = VisibleField("Someone Else", 0.4)
    assert roll_up(compare_fields(mixed, SIGNED, THRESHOLD)) is CheckStatus.FAILED


def test_confidence_must_be_between_zero_and_one():
    for bad in [-0.1, 1.1, float("nan")]:
        with pytest.raises(ValueError):
            VisibleField("x", bad)
