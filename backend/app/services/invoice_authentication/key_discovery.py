"""Find the verification keys an enrolled issuer has published, and decide if they are usable.

The rules, in order:
  1. The issuer domain must be valid.
  2. The domain must have an ACTIVE enrolment. No DNS lookup is made otherwise.
  3. Keys are read only from the TXT records at _verifigst.<domain>.
  4. Records that are malformed, or that repeat a key id, are ignored.
  5. Revoked keys, expired keys and keys that are not yet valid are never returned.
  6. A failed lookup is never a pass.

TRUSTED means only that at least one published key is usable. It says nothing yet about
whether any signature verifies.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .enrollment import Enrollment, EnrollmentRegistry, EnrollmentStatus
from .key_records import KeyRecord, KeyRecordError, parse_key_record
from .normalization import normalize_domain

RECORD_PREFIX = "_verifigst."


class LookupUnavailableError(Exception):
    """The DNS lookup could not be completed (timeout, server failure, no network)."""


class TxtResolver(Protocol):
    def lookup_txt(self, name: str) -> list[str]:
        """Return the TXT strings at this name, or [] if none. Raise LookupUnavailableError on failure."""
        ...


class StaticTxtResolver:
    """Answers from a fixed dictionary. For tests and offline demonstrations only."""

    def __init__(self, records: dict[str, list[str]] | None = None, *, unavailable: bool = False):
        self._records = {name.lower(): list(texts) for name, texts in (records or {}).items()}
        self._unavailable = unavailable
        self.lookups: list[str] = []

    def lookup_txt(self, name: str) -> list[str]:
        self.lookups.append(name)
        if self._unavailable:
            raise LookupUnavailableError("lookup unavailable")
        return list(self._records.get(name.lower(), []))


class DiscoveryStatus(str, Enum):
    TRUSTED = "trusted"
    INVALID_DOMAIN = "invalid_domain"
    NOT_ENROLLED = "not_enrolled"
    ENROLMENT_PENDING = "enrolment_pending"
    ENROLMENT_SUSPENDED = "enrolment_suspended"
    LOOKUP_UNAVAILABLE = "lookup_unavailable"
    NO_KEY = "no_key"
    KEY_REVOKED = "key_revoked"
    KEY_EXPIRED = "key_expired"
    KEY_NOT_YET_VALID = "key_not_yet_valid"


@dataclass(frozen=True)
class DiscoveredKey:
    key_id: str
    public_key: Ed25519PublicKey


@dataclass(frozen=True)
class KeyDiscoveryResult:
    status: DiscoveryStatus
    detail: str
    enrollment: Enrollment | None = None
    keys: tuple[DiscoveredKey, ...] = ()

    @property
    def is_trusted(self) -> bool:
        return self.status is DiscoveryStatus.TRUSTED


class KeyDiscoveryService:
    def __init__(self, resolver: TxtResolver, registry: EnrollmentRegistry) -> None:
        self._resolver = resolver
        self._registry = registry

    def discover(
        self, domain: str, on_date: date, key_id: str | None = None
    ) -> KeyDiscoveryResult:
        """Look up usable keys for an issuer domain as of on_date.

        on_date is normally the date of verification, which is the conservative choice:
        a key that has since expired is reported as expired, never as valid.
        """
        try:
            name = normalize_domain(domain)
        except ValueError:
            return KeyDiscoveryResult(DiscoveryStatus.INVALID_DOMAIN, "The issuer domain is not valid.")

        enrollment = self._registry.get(name)
        if enrollment is None:
            return KeyDiscoveryResult(
                DiscoveryStatus.NOT_ENROLLED,
                "The issuer is not enrolled. A key published in DNS is not trusted without enrolment.",
            )
        if enrollment.status is EnrollmentStatus.PENDING:
            return KeyDiscoveryResult(
                DiscoveryStatus.ENROLMENT_PENDING,
                "Enrolment is not complete: domain control has not been verified.",
                enrollment,
            )
        if enrollment.status is EnrollmentStatus.SUSPENDED:
            return KeyDiscoveryResult(
                DiscoveryStatus.ENROLMENT_SUSPENDED, "The issuer's enrolment is suspended.", enrollment
            )

        try:
            texts = self._resolver.lookup_txt(RECORD_PREFIX + name)
        except LookupUnavailableError:
            return KeyDiscoveryResult(
                DiscoveryStatus.LOOKUP_UNAVAILABLE,
                "The key lookup could not be completed. This is not a pass.",
                enrollment,
            )

        records: list[KeyRecord] = []
        ignored = 0
        for text in texts:
            try:
                records.append(parse_key_record(text))
            except KeyRecordError:
                ignored += 1

        # A key id published more than once is ambiguous, so every record using it is dropped.
        counts: dict[str, int] = {}
        for record in records:
            counts[record.key_id] = counts.get(record.key_id, 0) + 1
        unambiguous = [r for r in records if counts[r.key_id] == 1]
        ignored += len(records) - len(unambiguous)

        candidates = [r for r in unambiguous if key_id is None or r.key_id == key_id]
        if not candidates:
            return KeyDiscoveryResult(
                DiscoveryStatus.NO_KEY,
                f"No usable key record was found ({ignored} ignored as malformed or ambiguous).",
                enrollment,
            )

        usable: list[KeyRecord] = []
        revoked = expired = not_yet = 0
        for record in candidates:
            if record.is_revoked:
                revoked += 1
            elif record.not_before and on_date < record.not_before:
                not_yet += 1
            elif record.not_after and on_date > record.not_after:
                expired += 1
            else:
                usable.append(record)

        if usable:
            return KeyDiscoveryResult(
                DiscoveryStatus.TRUSTED,
                f"{len(usable)} usable key(s) published by an enrolled issuer.",
                enrollment,
                tuple(DiscoveredKey(r.key_id, r.public_key) for r in usable),
            )
        if revoked:
            return KeyDiscoveryResult(DiscoveryStatus.KEY_REVOKED, "The published key has been revoked.", enrollment)
        if expired:
            return KeyDiscoveryResult(DiscoveryStatus.KEY_EXPIRED, "The published key has expired.", enrollment)
        return KeyDiscoveryResult(
            DiscoveryStatus.KEY_NOT_YET_VALID, "The published key is not valid yet.", enrollment
        )
