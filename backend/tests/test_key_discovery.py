from datetime import date

import pytest

from app.services.invoice_authentication.enrollment import (
    Enrollment,
    EnrollmentStatus,
    InMemoryEnrollmentRegistry,
)
from app.services.invoice_authentication.key_discovery import (
    DiscoveryStatus,
    KeyDiscoveryService,
    StaticTxtResolver,
)
from app.services.invoice_authentication.keys import generate_private_key, public_key_to_base64
from app.services.invoice_authentication.signing import sign_payload
from app.services.invoice_authentication.verification import (
    SignatureStatus,
    verify_payload_signature,
)

DOMAIN = "grove-chemicals.example"
TODAY = date(2026, 10, 18)


def record(key, kid="k1", **extra) -> str:
    fields = {"v": "verifigst1", "kid": kid, "k": "ed25519", "p": public_key_to_base64(key.public_key())}
    fields.update(extra)
    return "; ".join(f"{name}={value}" for name, value in fields.items())


def enrolment(status=EnrollmentStatus.ACTIVE) -> Enrollment:
    verified = None if status is EnrollmentStatus.PENDING else date(2026, 1, 5)
    return Enrollment(DOMAIN, "Grove Chemicals", status, verified)


def make_service(texts=None, enrollment=None, unavailable=False, published_at=DOMAIN):
    records = {"_verifigst." + published_at: texts} if texts is not None else {}
    resolver = StaticTxtResolver(records, unavailable=unavailable)
    registry = InMemoryEnrollmentRegistry([enrollment] if enrollment else [])
    return KeyDiscoveryService(resolver, registry), resolver


def test_enrolled_issuer_with_a_valid_key_is_trusted():
    key = generate_private_key()
    service, _ = make_service([record(key, "k1")], enrolment())
    result = service.discover(DOMAIN, TODAY)
    assert result.status is DiscoveryStatus.TRUSTED
    assert result.is_trusted
    assert [k.key_id for k in result.keys] == ["k1"]
    assert public_key_to_base64(result.keys[0].public_key) == public_key_to_base64(key.public_key())
    assert result.enrollment.issuer_name == "Grove Chemicals"


def test_domain_names_are_case_insensitive():
    service, _ = make_service([record(generate_private_key())], enrolment())
    assert service.discover("GROVE-CHEMICALS.example", TODAY).is_trusted


def test_a_key_in_dns_is_not_trusted_without_enrolment_and_no_lookup_is_made():
    service, resolver = make_service([record(generate_private_key())], None)
    result = service.discover(DOMAIN, TODAY)
    assert result.status is DiscoveryStatus.NOT_ENROLLED
    assert result.keys == ()
    assert resolver.lookups == []


def test_pending_and_suspended_enrolments_are_not_trusted():
    for status, expected in [
        (EnrollmentStatus.PENDING, DiscoveryStatus.ENROLMENT_PENDING),
        (EnrollmentStatus.SUSPENDED, DiscoveryStatus.ENROLMENT_SUSPENDED),
    ]:
        service, resolver = make_service([record(generate_private_key())], enrolment(status))
        result = service.discover(DOMAIN, TODAY)
        assert result.status is expected
        assert result.keys == ()
        assert resolver.lookups == []


def test_an_active_enrolment_must_record_when_domain_control_was_verified():
    with pytest.raises(ValueError):
        Enrollment(DOMAIN, "Grove Chemicals", EnrollmentStatus.ACTIVE)


def test_invalid_domains_are_rejected_without_a_lookup():
    for bad in ["localhost", "not a domain", "", None]:
        service, resolver = make_service([record(generate_private_key())], enrolment())
        assert service.discover(bad, TODAY).status is DiscoveryStatus.INVALID_DOMAIN
        assert resolver.lookups == []


def test_records_published_under_another_domain_are_not_used():
    service, _ = make_service([record(generate_private_key())], enrolment(), published_at="other.example")
    assert service.discover(DOMAIN, TODAY).status is DiscoveryStatus.NO_KEY


def test_no_records_means_no_key():
    service, _ = make_service([], enrolment())
    result = service.discover(DOMAIN, TODAY)
    assert result.status is DiscoveryStatus.NO_KEY
    assert result.keys == ()


def test_malformed_records_are_ignored_and_never_trusted():
    only_garbage, _ = make_service(["garbage", "v=verifigst1; p=nope"], enrolment())
    assert only_garbage.discover(DOMAIN, TODAY).status is DiscoveryStatus.NO_KEY

    mixed, _ = make_service(["garbage", record(generate_private_key(), "good")], enrolment())
    result = mixed.discover(DOMAIN, TODAY)
    assert result.is_trusted
    assert [k.key_id for k in result.keys] == ["good"]


def test_a_failed_lookup_is_never_a_pass():
    service, _ = make_service([record(generate_private_key())], enrolment(), unavailable=True)
    result = service.discover(DOMAIN, TODAY)
    assert result.status is DiscoveryStatus.LOOKUP_UNAVAILABLE
    assert result.keys == ()


def test_revoked_expired_and_future_keys_are_not_returned():
    cases = [
        (record(generate_private_key(), rev="2026-09-01"), DiscoveryStatus.KEY_REVOKED),
        (record(generate_private_key(), na="2026-10-17"), DiscoveryStatus.KEY_EXPIRED),
        (record(generate_private_key(), nb="2026-10-19"), DiscoveryStatus.KEY_NOT_YET_VALID),
    ]
    for text, expected in cases:
        service, _ = make_service([text], enrolment())
        result = service.discover(DOMAIN, TODAY)
        assert result.status is expected
        assert result.keys == ()


def test_validity_window_includes_both_end_dates():
    service, _ = make_service([record(generate_private_key(), nb="2026-10-18", na="2026-10-18")], enrolment())
    assert service.discover(DOMAIN, TODAY).is_trusted


def test_a_revoked_key_wins_over_other_reasons_when_nothing_is_usable():
    texts = [
        record(generate_private_key(), "old", na="2026-01-01"),
        record(generate_private_key(), "bad", rev="2026-09-01"),
    ]
    service, _ = make_service(texts, enrolment())
    assert service.discover(DOMAIN, TODAY).status is DiscoveryStatus.KEY_REVOKED


def test_key_rotation_returns_only_the_usable_keys():
    old_revoked = record(generate_private_key(), "old", rev="2026-09-01")
    current_a = record(generate_private_key(), "a")
    current_b = record(generate_private_key(), "b")
    service, _ = make_service([old_revoked, current_a, current_b], enrolment())
    result = service.discover(DOMAIN, TODAY)
    assert result.is_trusted
    assert sorted(k.key_id for k in result.keys) == ["a", "b"]


def test_a_specific_key_id_can_be_requested():
    texts = [
        record(generate_private_key(), "a"),
        record(generate_private_key(), "b"),
        record(generate_private_key(), "gone", rev="2026-09-01"),
    ]
    service, _ = make_service(texts, enrolment())
    assert [k.key_id for k in service.discover(DOMAIN, TODAY, key_id="b").keys] == ["b"]
    assert service.discover(DOMAIN, TODAY, key_id="missing").status is DiscoveryStatus.NO_KEY
    assert service.discover(DOMAIN, TODAY, key_id="gone").status is DiscoveryStatus.KEY_REVOKED


def test_a_key_id_published_twice_is_ambiguous_and_dropped():
    duplicates = [record(generate_private_key(), "dup"), record(generate_private_key(), "dup")]
    only_dups, _ = make_service(duplicates, enrolment())
    assert only_dups.discover(DOMAIN, TODAY).status is DiscoveryStatus.NO_KEY

    with_unique, _ = make_service(duplicates + [record(generate_private_key(), "ok")], enrolment())
    result = with_unique.discover(DOMAIN, TODAY)
    assert result.is_trusted
    assert [k.key_id for k in result.keys] == ["ok"]


def test_discovered_key_verifies_the_enrolled_issuers_signature(payload, private_key):
    signature = sign_payload(private_key, payload)
    service, _ = make_service([record(private_key)], enrolment())
    result = service.discover(payload.issuer_domain, TODAY)
    assert result.is_trusted
    outcomes = [verify_payload_signature(k.public_key, payload, signature).status for k in result.keys]
    assert outcomes == [SignatureStatus.VALID]


def test_a_signature_from_a_key_the_issuer_did_not_publish_does_not_verify(payload):
    published = generate_private_key()
    impostor = generate_private_key()
    service, _ = make_service([record(published)], enrolment())
    result = service.discover(payload.issuer_domain, TODAY)
    signature = sign_payload(impostor, payload)
    outcomes = [verify_payload_signature(k.public_key, payload, signature).status for k in result.keys]
    assert outcomes == [SignatureStatus.INVALID]


def test_an_unenrolled_issuer_leaves_no_keys_to_verify_with(payload, private_key):
    service, _ = make_service([record(private_key)], None)
    result = service.discover(payload.issuer_domain, TODAY)
    assert not result.is_trusted
    assert result.keys == ()
