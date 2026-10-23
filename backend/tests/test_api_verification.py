from fastapi.testclient import TestClient

from app.main import create_app
from app.services.invoice_authentication.keys import generate_private_key
from app.services.invoice_authentication.payload import InvoicePayloadV1
from app.services.invoice_authentication.signing import sign_payload

client = TestClient(create_app())

SAMPLE_IDS = ["intact", "amount", "account", "bad-signature", "unknown-key", "low-confidence", "repeated"]

EXPECTED = {
    "intact": {
        "field_extraction": "passed",
        "issuer_key": "passed",
        "signature": "passed",
        "issuer_identity": "passed",
        "payload_comparison": "passed",
        "duplicate_reference": "passed",
        "official_einvoice": "not_checked",
    },
    "amount": {"signature": "passed", "payload_comparison": "failed"},
    "account": {"signature": "passed", "payload_comparison": "failed"},
    "bad-signature": {
        "issuer_key": "passed",
        "signature": "failed",
        "issuer_identity": "not_checked",
        "payload_comparison": "not_checked",
    },
    "unknown-key": {
        "issuer_key": "unknown",
        "signature": "unknown",
        "issuer_identity": "not_checked",
        "payload_comparison": "not_checked",
    },
    "low-confidence": {
        "field_extraction": "manual_review",
        "signature": "passed",
        "payload_comparison": "manual_review",
    },
    "repeated": {
        "signature": "passed",
        "payload_comparison": "passed",
        "duplicate_reference": "manual_review",
    },
}


def check_statuses(body):
    return {c["id"]: c["status"] for c in body["checks"]}


def field_statuses(body):
    return {f["field"]: f["status"] for f in body["field_comparisons"]}


def test_the_sample_invoices_are_listed_in_order():
    response = client.get("/api/v1/demo/samples")
    assert response.status_code == 200
    samples = response.json()
    assert [s["id"] for s in samples] == SAMPLE_IDS
    assert all(len(s["visible"]) == 8 for s in samples)


def test_unclear_fields_are_marked_in_the_low_confidence_sample():
    samples = {s["id"]: s for s in client.get("/api/v1/demo/samples").json()}
    unclear = {f["field"] for f in samples["low-confidence"]["visible"] if f["unclear"]}
    assert unclear == {"invoice_number", "total_amount"}
    assert not any(f["unclear"] for f in samples["intact"]["visible"])


def test_every_sample_gives_the_expected_results_through_the_real_pipeline():
    for sample_id, expected in EXPECTED.items():
        response = client.post(f"/api/v1/demo/samples/{sample_id}/verify")
        assert response.status_code == 200, sample_id
        statuses = check_statuses(response.json())
        for check_id, status in expected.items():
            assert statuses[check_id] == status, (sample_id, check_id)


def test_the_amount_sample_flags_only_the_amount():
    body = client.post("/api/v1/demo/samples/amount/verify").json()
    failed = [field for field, status in field_statuses(body).items() if status == "failed"]
    assert failed == ["total_amount"]
    assert any("independent channel" in action for action in body["next_actions"])


def test_the_repeated_sample_names_the_earlier_records():
    body = client.post("/api/v1/demo/samples/repeated/verify").json()
    detail = next(c["detail"] for c in body["checks"] if c["id"] == "duplicate_reference")
    assert "REC-D-001" in detail and "REC-D-002" in detail


def test_unknown_and_badly_formed_sample_ids_are_rejected():
    assert client.post("/api/v1/demo/samples/nope/verify").status_code == 404
    assert client.post("/api/v1/demo/samples/Bad_ID/verify").status_code == 422
    assert client.post("/api/v1/demo/samples/" + "x" * 50 + "/verify").status_code == 422


def test_the_response_has_no_overall_verdict_and_only_the_documented_keys():
    body = client.post("/api/v1/demo/samples/intact/verify").json()
    assert set(body) == {"checks", "field_comparisons", "next_actions"}
    assert all(set(c) == {"id", "label", "status", "detail"} for c in body["checks"])


def test_an_empty_request_is_accepted_and_nothing_is_checked():
    response = client.post("/api/v1/verifications", json={})
    assert response.status_code == 200
    assert set(check_statuses(response.json()).values()) == {"not_checked"}


def test_a_malformed_signed_payload_is_reported_not_crashed():
    body = {"envelope": {"payload": {"issuer_domain": "grove-chemicals.example"}, "signature": "AAAA"}}
    response = client.post("/api/v1/verifications", json=body)
    assert response.status_code == 200
    statuses = check_statuses(response.json())
    assert statuses["signature"] == "failed"
    assert statuses["issuer_key"] == "not_checked"


def test_an_unenrolled_issuers_signed_invoice_is_unknown_never_a_pass():
    fields = {
        "issuer_name": "Unlisted Traders",
        "issuer_domain": "unlisted-traders.example",
        "invoice_number": "SYN-2026-0300",
        "invoice_date": "2026-10-02",
        "buyer_name": "Hazel Components",
        "currency": "INR",
        "total_amount": "1000.00",
        "tax_amount": "152.54",
        "payment_account": "SYNTH000001111",
        "document_reference": None,
    }
    signature = sign_payload(generate_private_key(), InvoicePayloadV1(**fields))
    visible = {
        name: {"value": None if value is None else str(value), "confidence": 0.99}
        for name, value in fields.items()
        if name != "document_reference" and name != "issuer_domain"
    }
    body = {"visible": visible, "envelope": {"payload": fields, "signature": signature, "key_id": "k1"}}
    response = client.post("/api/v1/verifications", json=body)
    assert response.status_code == 200
    statuses = check_statuses(response.json())
    assert statuses["field_extraction"] == "passed"
    assert statuses["issuer_key"] == "unknown"
    assert statuses["signature"] == "unknown"
    assert statuses["payload_comparison"] == "not_checked"


def test_invalid_requests_are_rejected_with_422():
    long_signature = "A" * 201
    bad_bodies = [
        {"visible": {"total_amount": {"value": "1", "confidence": 1.5}}},
        {"visible": {"total_amount": {"value": "1", "confidence": -0.1}}},
        {"visible": {"total_amount": {"value": "x" * 501, "confidence": 0.9}}},
        {"visible": {"not_a_field": {"value": "1", "confidence": 0.9}}},
        {"surprise": True},
        {"file_sha256": "xyz"},
        {"envelope": {"payload": {}, "signature": long_signature}},
        {"envelope": {"payload": {f"k{i}": "v" for i in range(31)}, "signature": "AAAA"}},
        {"envelope": {"payload": {}}},
    ]
    for body in bad_bodies:
        assert client.post("/api/v1/verifications", json=body).status_code == 422, body


def test_the_local_frontend_origin_is_allowed():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origins_get_no_cors_permission():
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_is_answered_only_for_allowed_origins():
    request_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    allowed = client.options(
        "/api/v1/verifications", headers={"Origin": "http://localhost:5173", **request_headers}
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.options(
        "/api/v1/verifications", headers={"Origin": "http://evil.example", **request_headers}
    )
    assert denied.status_code == 400
