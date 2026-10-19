import base64
from datetime import date

import pytest

from app.services.invoice_authentication.key_records import KeyRecordError, parse_key_record
from app.services.invoice_authentication.keys import generate_private_key, public_key_to_base64


def new_public_key_text() -> str:
    return public_key_to_base64(generate_private_key().public_key())


def make_record(**overrides) -> str:
    fields = {"v": "verifigst1", "kid": "2026a", "k": "ed25519", "p": new_public_key_text()}
    fields.update(overrides)
    return "; ".join(f"{name}={value}" for name, value in fields.items() if value is not None)


def test_minimal_record_parses():
    key = generate_private_key()
    record = parse_key_record(make_record(p=public_key_to_base64(key.public_key())))
    assert record.key_id == "2026a"
    assert public_key_to_base64(record.public_key) == public_key_to_base64(key.public_key())
    assert record.not_before is None
    assert record.not_after is None
    assert record.revoked_on is None
    assert record.is_revoked is False


def test_optional_dates_parse():
    record = parse_key_record(make_record(nb="2026-01-01", na="2027-01-01", rev="2026-09-01"))
    assert record.not_before == date(2026, 1, 1)
    assert record.not_after == date(2027, 1, 1)
    assert record.revoked_on == date(2026, 9, 1)
    assert record.is_revoked is True


def test_tag_case_spacing_and_trailing_semicolon_are_tolerated():
    text = f"  V=VERIFIGST1 ;KID=Key-1;K=ED25519 ; p={new_public_key_text()} ;"
    assert parse_key_record(text).key_id == "Key-1"


def test_bad_records_are_rejected():
    bad_records = [
        None,
        123,
        "",
        "   ",
        "random text that happens to be in dns",
        make_record(v="verifigst2"),
        make_record(v=None),
        make_record(kid=None),
        make_record(kid="has space"),
        make_record(kid="x" * 33),
        make_record(kid="caf\u00e9"),
        make_record(k="rsa"),
        make_record(k=None),
        make_record(p=None),
        make_record(p="!!!"),
        make_record(p=base64.b64encode(b"x" * 31).decode("ascii")),
        make_record(extra="1"),
        make_record(nb="2026-13-01"),
        make_record(nb="2027-01-01", na="2026-01-01"),
        make_record(rev="yesterday"),
        make_record() + "; kid=other",
        make_record() + "; na=",
        "v=verifigst1; kid=a; k=ed25519; p=" + "A" * 600,
    ]
    for text in bad_records:
        with pytest.raises(KeyRecordError):
            parse_key_record(text)
