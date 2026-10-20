"""Duplicate detection that keeps three different situations apart.

  same file       the identical file bytes were seen before
  same payload    the identical signed content was seen before (possibly a different file)
  reused number   the same issuer and invoice number appeared with different signed content

A duplicate document does not by itself prove a duplicate payment or fraud, so a hit
asks for manual review and is never reported as a failure.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SeenInvoice:
    record_id: str
    issuer_domain: str | None = None
    invoice_number: str | None = None
    payload_sha256: str | None = None
    file_sha256: str | None = None


class DuplicateIndex(Protocol):
    def find(
        self,
        *,
        file_sha256: str | None,
        payload_sha256: str | None,
        issuer_domain: str | None,
        invoice_number: str | None,
    ) -> list[SeenInvoice]:
        """Return earlier records that share the file, the payload or the reference."""
        ...


class InMemoryDuplicateIndex:
    """Held in memory. Used for tests and local demonstrations."""

    def __init__(self, seen: Iterable[SeenInvoice] = ()) -> None:
        self._seen: list[SeenInvoice] = list(seen)

    def add(self, record: SeenInvoice) -> None:
        self._seen.append(record)

    def find(
        self,
        *,
        file_sha256: str | None,
        payload_sha256: str | None,
        issuer_domain: str | None,
        invoice_number: str | None,
    ) -> list[SeenInvoice]:
        matches = []
        for record in self._seen:
            same_file = file_sha256 is not None and record.file_sha256 == file_sha256
            same_payload = payload_sha256 is not None and record.payload_sha256 == payload_sha256
            same_reference = (
                issuer_domain is not None
                and invoice_number is not None
                and record.issuer_domain == issuer_domain
                and record.invoice_number == invoice_number
            )
            if same_file or same_payload or same_reference:
                matches.append(record)
        return matches
