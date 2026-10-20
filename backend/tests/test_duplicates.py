from app.services.invoice_authentication.duplicates import InMemoryDuplicateIndex, SeenInvoice


def find(index, **overrides):
    criteria = dict(file_sha256=None, payload_sha256=None, issuer_domain=None, invoice_number=None)
    criteria.update(overrides)
    return index.find(**criteria)


def test_nothing_matches_an_empty_index():
    assert find(InMemoryDuplicateIndex(), file_sha256="a" * 64) == []


def test_matches_by_file_hash_payload_hash_or_reference():
    index = InMemoryDuplicateIndex(
        [
            SeenInvoice("R1", file_sha256="f" * 64),
            SeenInvoice("R2", payload_sha256="p" * 64),
            SeenInvoice("R3", issuer_domain="a.example", invoice_number="N1"),
        ]
    )
    assert [r.record_id for r in find(index, file_sha256="f" * 64)] == ["R1"]
    assert [r.record_id for r in find(index, payload_sha256="p" * 64)] == ["R2"]
    assert [r.record_id for r in find(index, issuer_domain="a.example", invoice_number="N1")] == ["R3"]


def test_a_reference_needs_both_the_issuer_and_the_number_to_match():
    index = InMemoryDuplicateIndex([SeenInvoice("R3", issuer_domain="a.example", invoice_number="N1")])
    assert find(index, issuer_domain="a.example", invoice_number="N2") == []
    assert find(index, issuer_domain="b.example", invoice_number="N1") == []


def test_missing_criteria_never_match_missing_fields():
    index = InMemoryDuplicateIndex([SeenInvoice("R1")])
    assert find(index) == []


def test_added_records_can_be_found():
    index = InMemoryDuplicateIndex()
    index.add(SeenInvoice("R9", file_sha256="z" * 64))
    assert [r.record_id for r in find(index, file_sha256="z" * 64)] == ["R9"]
