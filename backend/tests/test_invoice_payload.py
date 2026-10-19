from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.services.invoice_authentication.canonical import canonical_json_bytes
from app.services.invoice_authentication.payload import InvoicePayloadV1

GOLDEN_CANONICAL = (
    b'{"buyer_name":"Hazel Components","currency":"INR","document_reference":"DOC-SYN-0142",'
    b'"invoice_date":"2026-10-02","invoice_number":"SYN-2026-0142",'
    b'"issuer_domain":"grove-chemicals.example","issuer_name":"Grove Chemicals",'
    b'"payload_version":"verifigst.invoice.v1","payment_account":"SYNTH000005521",'
    b'"tax_amount":"97627.12","total_amount":"640000.00"}'
)


def build(fields, **changes):
    return InvoicePayloadV1(**{**fields, **changes})


def test_canonical_bytes_match_the_golden_value(payload):
    # If this fails, the signed byte format changed and old signatures would stop verifying.
    assert canonical_json_bytes(payload.canonical_fields()) == GOLDEN_CANONICAL


def test_canonical_bytes_do_not_depend_on_input_order(valid_fields):
    reordered = dict(reversed(list(valid_fields.items())))
    assert canonical_json_bytes(build(reordered).canonical_fields()) == canonical_json_bytes(
        build(valid_fields).canonical_fields()
    )


def test_inputs_are_normalized(valid_fields):
    p = build(
        valid_fields,
        issuer_domain=" Grove-Chemicals.EXAMPLE. ",
        currency="inr",
        buyer_name="  Hazel   Components ",
        payment_account="synth 0000-05521",
        total_amount="640000",
    )
    assert p.issuer_domain == "grove-chemicals.example"
    assert p.currency == "INR"
    assert p.buyer_name == "Hazel Components"
    assert p.payment_account == "SYNTH000005521"
    assert p.canonical_fields()["total_amount"] == "640000.00"


@pytest.mark.parametrize(
    "given, expected",
    [
        ("640000", "640000.00"),
        ("640000.5", "640000.50"),
        (Decimal("640000.50"), "640000.50"),
        (640000, "640000.00"),
    ],
)
def test_amounts_are_written_with_exactly_two_decimals(valid_fields, given, expected):
    assert build(valid_fields, total_amount=given).canonical_fields()["total_amount"] == expected


@pytest.mark.parametrize("field", ["total_amount", "tax_amount"])
@pytest.mark.parametrize(
    "bad",
    [640000.0, "640000.001", "-1.00", "1e5", "abc", "", "NaN", True, None, Decimal("NaN"), "1,000.00"],
)
def test_bad_amounts_are_rejected(valid_fields, field, bad):
    with pytest.raises(ValidationError):
        build(valid_fields, **{field: bad})


def test_total_must_be_greater_than_zero(valid_fields):
    with pytest.raises(ValidationError):
        build(valid_fields, total_amount="0.00", tax_amount="0.00")


def test_tax_cannot_exceed_total(valid_fields):
    with pytest.raises(ValidationError):
        build(valid_fields, tax_amount="640000.01")


def test_zero_tax_is_allowed(valid_fields):
    assert build(valid_fields, tax_amount="0.00").canonical_fields()["tax_amount"] == "0.00"


@pytest.mark.parametrize("bad", ["02/10/2026", "2026-13-01", "2026-1-2", datetime(2026, 10, 2), 20261002])
def test_bad_dates_are_rejected(valid_fields, bad):
    with pytest.raises(ValidationError):
        build(valid_fields, invoice_date=bad)


@pytest.mark.parametrize("bad", ["localhost", "bad_domain.example", "exa mple.com", "m\u00fcnchen.example", ""])
def test_bad_domains_are_rejected(valid_fields, bad):
    with pytest.raises(ValidationError):
        build(valid_fields, issuer_domain=bad)


@pytest.mark.parametrize("bad", ["", "has space", "x" * 65, "-leading", "semi;colon"])
def test_bad_invoice_numbers_are_rejected(valid_fields, bad):
    with pytest.raises(ValidationError):
        build(valid_fields, invoice_number=bad)


def test_invisible_characters_in_names_are_rejected(valid_fields):
    with pytest.raises(ValidationError):
        build(valid_fields, buyer_name="Hazel\u200bComponents")


def test_unknown_fields_are_rejected(valid_fields):
    with pytest.raises(ValidationError):
        InvoicePayloadV1(**valid_fields, surprise="x")


def test_missing_required_field_is_rejected(valid_fields):
    del valid_fields["issuer_name"]
    with pytest.raises(ValidationError):
        InvoicePayloadV1(**valid_fields)


def test_unsupported_payload_version_is_rejected(valid_fields):
    with pytest.raises(ValidationError):
        build(valid_fields, payload_version="verifigst.invoice.v2")


def test_optional_fields_can_be_absent_and_are_written_as_null(valid_fields):
    p = build(valid_fields, payment_account=None, document_reference=None)
    fields = p.canonical_fields()
    assert fields["payment_account"] is None
    assert fields["document_reference"] is None
    assert b'"payment_account":null' in canonical_json_bytes(fields)


def test_payload_cannot_be_changed_after_creation(payload):
    with pytest.raises(ValidationError):
        payload.total_amount = Decimal("1.00")
