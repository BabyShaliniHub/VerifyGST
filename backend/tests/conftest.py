import pytest

from app.services.invoice_authentication.keys import generate_private_key
from app.services.invoice_authentication.payload import InvoicePayloadV1

# Synthetic values only. They describe no real company, invoice or account.
VALID_FIELDS = {
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


@pytest.fixture
def valid_fields() -> dict:
    return dict(VALID_FIELDS)


@pytest.fixture
def payload(valid_fields) -> InvoicePayloadV1:
    return InvoicePayloadV1(**valid_fields)


@pytest.fixture
def private_key():
    return generate_private_key()
