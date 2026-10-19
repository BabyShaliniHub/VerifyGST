"""Issuer enrolment: which domains VerifiGST treats as known issuers.

Enrolment is the trust anchor. A key found in DNS is only considered for a domain
that has an ACTIVE enrolment, and an ACTIVE enrolment records when domain control
was verified (for example, by a challenge value the issuer placed in its DNS zone).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Protocol

from .normalization import normalize_domain


class EnrollmentStatus(str, Enum):
    PENDING = "pending"  # enrolment started, domain control not yet proven
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class Enrollment:
    domain: str
    issuer_name: str
    status: EnrollmentStatus
    domain_control_verified_on: date | None = None

    def __post_init__(self) -> None:
        if self.status is EnrollmentStatus.ACTIVE and self.domain_control_verified_on is None:
            raise ValueError("an active enrolment needs a domain-control verification date")


class EnrollmentRegistry(Protocol):
    def get(self, domain: str) -> Enrollment | None: ...


class InMemoryEnrollmentRegistry:
    """A registry held in memory. Used for tests and local demonstrations."""

    def __init__(self, enrollments: Iterable[Enrollment] = ()) -> None:
        self._by_domain = {normalize_domain(e.domain): e for e in enrollments}

    def get(self, domain: str) -> Enrollment | None:
        try:
            key = normalize_domain(domain)
        except ValueError:
            return None
        return self._by_domain.get(key)
