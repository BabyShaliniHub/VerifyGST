"""Turn a trading cycle into an explained finding for a human reviewer.

Everything here is decision support. A closed trading loop, and every signal below, is an
indicator that deserves a look. None of it is proof of fraud: each signal comes with what it may
indicate and, just as important, what it does not prove.

The review priority ranks which loops to look at first. It counts how many additional signals
were found and is not a probability that anything is wrong.

Checks that could not be evaluated are listed in `not_evaluated`. They are never treated as passed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.graph.cycles import Cycle

# Tunable thresholds. Each one is a judgement call, so each is named and tested at its boundary.
SIMILAR_AMOUNT_TOLERANCE_BPS = 200  # amounts within 2% of the largest count as "similar"
TIGHT_TIMING_DAYS = 7  # the whole loop closing within a week counts as tight

DISCLAIMER = (
    "This is an indicator for human review, not proof of fraud. Every signal can have an "
    "innocent explanation."
)
PRIORITY_EXPLANATION = (
    "Review priority ranks which loops to look at first, from the number of additional signals "
    "found. It is not a probability that anything is wrong."
)


@dataclass(frozen=True)
class TransactionFact:
    id: str
    seller_id: str
    buyer_id: str
    invoice_reference: str | None
    amount_minor: int  # integer paise
    currency: str
    occurred_on: date
    evidence_level: str  # complete, partial or missing, as recorded


@dataclass(frozen=True)
class Signal:
    code: str
    title: str
    observed: str  # what the data shows
    may_indicate: str  # why a reviewer might care
    does_not_prove: str  # the innocent explanations
    transaction_ids: tuple[str, ...]


@dataclass(frozen=True)
class NotEvaluated:
    code: str
    reason: str


@dataclass(frozen=True)
class Finding:
    company_ids: tuple[str, ...]
    company_names: tuple[str, ...]
    transaction_ids: tuple[str, ...]
    summary: str
    priority: str  # low, medium or high
    priority_explanation: str
    signals: tuple[Signal, ...]
    not_evaluated: tuple[NotEvaluated, ...]
    disclaimer: str

    @property
    def length(self) -> int:
        return len(self.company_ids)


def _money(amount_minor: int, currency: str) -> str:
    return f"{currency} {Decimal(amount_minor) / 100:,.2f}"


def _evidence_signal(facts: list[TransactionFact]) -> Signal | None:
    missing = [f for f in facts if f.evidence_level == "missing"]
    partial = [f for f in facts if f.evidence_level == "partial"]
    # Triggered by any missing evidence, or when at least half the transactions are only partial.
    if not missing and len(partial) * 2 < len(facts):
        return None
    return Signal(
        code="evidence_gaps",
        title="Evidence is missing or incomplete",
        observed=(
            f"Evidence recorded for the {len(facts)} transactions: {len(missing)} missing, "
            f"{len(partial)} partial, {len(facts) - len(missing) - len(partial)} complete."
        ),
        may_indicate=(
            "Without supporting invoices the trades cannot be checked, so the loop cannot be "
            "confirmed as genuine commerce."
        ),
        does_not_prove=(
            "Missing evidence can simply mean the documents have not been uploaded or linked yet."
        ),
        transaction_ids=tuple(f.id for f in facts if f.evidence_level in ("missing", "partial")),
    )


def _reference_signal(facts: list[TransactionFact]) -> Signal | None:
    by_reference: dict[str, list[str]] = {}
    for fact in facts:
        if fact.invoice_reference:
            by_reference.setdefault(fact.invoice_reference, []).append(fact.id)
    repeated = {ref: ids for ref, ids in by_reference.items() if len(ids) > 1}
    if not repeated:
        return None
    observed = " ".join(
        f"Invoice reference {ref} appears on {len(ids)} transactions in this loop."
        for ref, ids in sorted(repeated.items())
    )
    return Signal(
        code="repeated_invoice_reference",
        title="The same invoice reference is used more than once",
        observed=observed,
        may_indicate=(
            "One invoice should normally support one sale. Reusing it can mean the same paper is "
            "being used to justify several movements of money."
        ),
        does_not_prove=(
            "A reference can be reused by mistake, or for staged deliveries under one order."
        ),
        transaction_ids=tuple(i for ids in repeated.values() for i in ids),
    )


def _amount_signal(facts: list[TransactionFact]) -> tuple[Signal | None, NotEvaluated | None]:
    currencies = {f.currency for f in facts}
    if len(currencies) > 1:
        return None, NotEvaluated(
            "similar_amounts",
            "The transactions use different currencies, so their amounts cannot be compared directly.",
        )
    low = min(f.amount_minor for f in facts)
    high = max(f.amount_minor for f in facts)
    if high <= 0 or (high - low) * 10_000 > high * SIMILAR_AMOUNT_TOLERANCE_BPS:
        return None, None
    currency = facts[0].currency
    spread = Decimal((high - low) * 100) / Decimal(high)
    return (
        Signal(
            code="similar_amounts",
            title="The amounts barely change around the loop",
            observed=(
                f"Amounts range from {_money(low, currency)} to {_money(high, currency)}, "
                f"a spread of {spread:.2f}% of the largest."
            ),
            may_indicate=(
                "Value that goes round a loop and comes back almost unchanged is a pattern seen "
                "when sales are circular and no real goods change hands."
            ),
            does_not_prove=(
                "Fixed-price supply agreements, or pass-through trading with a thin margin, can "
                "produce similar amounts."
            ),
            transaction_ids=tuple(f.id for f in facts),
        ),
        None,
    )


def _timing_signal(facts: list[TransactionFact]) -> Signal | None:
    first = min(f.occurred_on for f in facts)
    last = max(f.occurred_on for f in facts)
    days = (last - first).days
    if days > TIGHT_TIMING_DAYS:
        return None
    return Signal(
        code="tight_timing",
        title="The whole loop closes within days",
        observed=(
            f"All {len(facts)} transactions fall within {days} day(s), from "
            f"{first.isoformat()} to {last.isoformat()}."
        ),
        may_indicate=(
            "A loop that closes within days leaves little time for goods to be produced, moved or "
            "sold on."
        ),
        does_not_prove=(
            "Fast turnaround is normal in some trades, for example commodity trading or "
            "just-in-time supply."
        ),
        transaction_ids=tuple(f.id for f in facts),
    )


def _priority(signal_count: int) -> str:
    if signal_count == 0:
        return "low"
    if signal_count == 1:
        return "medium"
    return "high"


def build_finding(
    cycle: Cycle,
    facts_by_id: Mapping[str, TransactionFact],
    names_by_id: Mapping[str, str],
) -> Finding:
    """Explain one cycle. Raises ValueError if any record the cycle refers to is missing."""
    missing_transactions = [i for i in cycle.transaction_ids if i not in facts_by_id]
    missing_companies = [i for i in cycle.company_ids if i not in names_by_id]
    if missing_transactions or missing_companies:
        raise ValueError(
            "The cycle refers to records that were not provided: "
            f"{len(missing_transactions)} transaction(s), {len(missing_companies)} company name(s)."
        )

    facts = [facts_by_id[i] for i in cycle.transaction_ids]
    names = tuple(names_by_id[i] for i in cycle.company_ids)

    amount_signal, amount_not_evaluated = _amount_signal(facts)
    candidates = [
        _evidence_signal(facts),
        _reference_signal(facts),
        amount_signal,
        _timing_signal(facts),
    ]
    signals = tuple(s for s in candidates if s is not None)
    not_evaluated = (amount_not_evaluated,) if amount_not_evaluated else ()

    loop = " -> ".join((*names, names[0]))
    return Finding(
        company_ids=cycle.company_ids,
        company_names=names,
        transaction_ids=cycle.transaction_ids,
        summary=f"{len(names)} companies trade in a closed loop: {loop}.",
        priority=_priority(len(signals)),
        priority_explanation=PRIORITY_EXPLANATION,
        signals=signals,
        not_evaluated=not_evaluated,
        disclaimer=DISCLAIMER,
    )


@dataclass(frozen=True)
class CheckResult:
    code: str
    title: str
    result: str  # triggered, not_triggered or not_evaluated


# Every check that runs on a cycle, in display order. The titles must match the signal titles.
CHECKS = (
    ("evidence_gaps", "Evidence is missing or incomplete"),
    ("repeated_invoice_reference", "The same invoice reference is used more than once"),
    ("similar_amounts", "The amounts barely change around the loop"),
    ("tight_timing", "The whole loop closes within days"),
)


def check_results(finding: Finding) -> tuple[CheckResult, ...]:
    """Every check that ran, so a quiet finding reads as 'checked, nothing triggered', never as 'cleared'."""
    triggered = {signal.code for signal in finding.signals}
    skipped = {item.code for item in finding.not_evaluated}
    results = []
    for code, title in CHECKS:
        if code in triggered:
            state = "triggered"
        elif code in skipped:
            state = "not_evaluated"
        else:
            state = "not_triggered"
        results.append(CheckResult(code, title, state))
    return tuple(results)
