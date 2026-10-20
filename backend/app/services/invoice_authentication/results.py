"""Result types shared by every verification check.

The statuses match the five states the Verify Invoice page already shows. There is
deliberately no overall verdict: each check keeps its own result so that a pass in one
place is never read as proof about something else.
"""

from dataclasses import dataclass
from enum import Enum


class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_CHECKED = "not_checked"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class CheckOutcome:
    check_id: str
    label: str
    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class FieldComparison:
    field: str
    visible: str | None
    signed: str | None
    status: CheckStatus


@dataclass(frozen=True)
class ProviderOutcome:
    """What an external verification provider reports."""

    status: CheckStatus
    detail: str


@dataclass(frozen=True)
class VerificationReport:
    checks: tuple[CheckOutcome, ...]
    fields: tuple[FieldComparison, ...]
    next_actions: tuple[str, ...]

    def check(self, check_id: str) -> CheckOutcome:
        for outcome in self.checks:
            if outcome.check_id == check_id:
                return outcome
        raise KeyError(check_id)
