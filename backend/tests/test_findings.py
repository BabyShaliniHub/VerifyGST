from datetime import date, timedelta

import pytest

from app.analysis.findings import (
    DISCLAIMER,
    SIMILAR_AMOUNT_TOLERANCE_BPS,
    TIGHT_TIMING_DAYS,
    TransactionFact,
    build_finding,
)
from app.graph.cycles import Cycle
from app.seed.demo_data import COMPANIES, TRANSACTIONS, stable_id

NAMES = {str(stable_id("company", c.key)): c.name for c in COMPANIES}


def demo_finding(company_keys, transaction_keys):
    facts = {}
    for t in TRANSACTIONS:
        tid = str(stable_id("transaction", t.key))
        facts[tid] = TransactionFact(
            id=tid,
            seller_id=str(stable_id("company", t.seller_key)),
            buyer_id=str(stable_id("company", t.buyer_key)),
            invoice_reference=t.invoice_reference,
            amount_minor=int(t.amount * 100),
            currency="INR",
            occurred_on=t.occurred_on,
            evidence_level=t.evidence_level,
        )
    cycle = Cycle(
        tuple(str(stable_id("company", k)) for k in company_keys),
        tuple(str(stable_id("transaction", k)) for k in transaction_keys),
    )
    return build_finding(cycle, facts, NAMES), cycle


def make_finding(*, evidence=None, amounts=None, offsets=None, currencies=None, references=None):
    """A three-company loop with innocent defaults, so a test changes only what it cares about."""
    evidence = evidence or ["complete"] * 3
    amounts = amounts or [10_000_000, 15_000_000, 20_000_000]
    offsets = offsets or [0, 30, 60]
    currencies = currencies or ["INR"] * 3
    references = references or ["REF-0", "REF-1", "REF-2"]
    facts = {
        f"t{i}": TransactionFact(
            id=f"t{i}",
            seller_id=f"c{i}",
            buyer_id=f"c{(i + 1) % 3}",
            invoice_reference=references[i],
            amount_minor=amounts[i],
            currency=currencies[i],
            occurred_on=date(2026, 9, 1) + timedelta(days=offsets[i]),
            evidence_level=evidence[i],
        )
        for i in range(3)
    }
    cycle = Cycle(("c0", "c1", "c2"), ("t0", "t1", "t2"))
    return build_finding(cycle, facts, {"c0": "Zero Ltd", "c1": "One Ltd", "c2": "Two Ltd"})


def codes(finding):
    return [signal.code for signal in finding.signals]


def test_the_complete_demo_cycle_has_no_extra_signals_and_low_priority():
    finding, _ = demo_finding(["C1", "C2", "C3"], ["T1", "T2", "T3"])
    assert codes(finding) == []
    assert finding.priority == "low"
    assert finding.not_evaluated == ()


def test_the_suspicious_demo_cycle_has_all_four_signals_and_high_priority():
    finding, _ = demo_finding(["C4", "C5", "C6"], ["T4", "T5", "T6"])
    assert codes(finding) == [
        "evidence_gaps",
        "repeated_invoice_reference",
        "similar_amounts",
        "tight_timing",
    ]
    assert finding.priority == "high"


def test_the_finding_names_the_companies_and_points_at_the_right_transactions():
    finding, cycle = demo_finding(["C4", "C5", "C6"], ["T4", "T5", "T6"])
    assert finding.company_names == ("Dune Textiles", "Elm Packaging", "Fern Agro")
    assert finding.summary == (
        "3 companies trade in a closed loop: Dune Textiles -> Elm Packaging -> Fern Agro -> Dune Textiles."
    )
    by_code = {s.code: s for s in finding.signals}
    t = lambda *keys: {str(stable_id("transaction", k)) for k in keys}
    assert set(by_code["repeated_invoice_reference"].transaction_ids) == t("T5", "T6")
    assert set(by_code["evidence_gaps"].transaction_ids) == t("T4", "T5", "T6")
    assert "INV-D-202" in by_code["repeated_invoice_reference"].observed
    assert "4,800,000.00" in by_code["similar_amounts"].observed
    assert "4,780,000.00" in by_code["similar_amounts"].observed
    assert "2026-09-10" in by_code["tight_timing"].observed
    for signal in finding.signals:
        assert set(signal.transaction_ids) <= set(cycle.transaction_ids)


def test_every_signal_says_what_it_does_not_prove_and_the_finding_says_it_is_not_proof():
    finding, _ = demo_finding(["C4", "C5", "C6"], ["T4", "T5", "T6"])
    assert "not proof" in finding.disclaimer
    assert finding.disclaimer == DISCLAIMER
    assert "not a probability" in finding.priority_explanation
    for signal in finding.signals:
        assert signal.observed and signal.may_indicate and signal.does_not_prove


@pytest.mark.parametrize(
    "evidence, expected",
    [
        (["complete", "complete", "complete"], False),
        (["complete", "complete", "missing"], True),
        (["complete", "partial", "complete"], False),
        (["partial", "partial", "complete"], True),
        (["partial", "partial", "partial"], True),
    ],
)
def test_the_evidence_rule_at_its_boundaries(evidence, expected):
    assert ("evidence_gaps" in codes(make_finding(evidence=evidence))) is expected


def test_the_amount_rule_includes_the_tolerance_boundary_and_excludes_just_beyond_it():
    high = 1_000_000
    on_the_boundary = high - high * SIMILAR_AMOUNT_TOLERANCE_BPS // 10_000
    assert "similar_amounts" in codes(make_finding(amounts=[high, high, on_the_boundary]))
    assert "similar_amounts" not in codes(make_finding(amounts=[high, high, on_the_boundary - 1]))


def test_the_timing_rule_includes_the_limit_and_excludes_one_day_beyond_it():
    assert "tight_timing" in codes(make_finding(offsets=[0, 3, TIGHT_TIMING_DAYS]))
    assert "tight_timing" not in codes(make_finding(offsets=[0, 3, TIGHT_TIMING_DAYS + 1]))


def test_mixed_currencies_are_reported_as_not_evaluated_and_never_as_a_pass():
    finding = make_finding(currencies=["INR", "INR", "USD"], amounts=[1_000_000] * 3)
    assert "similar_amounts" not in codes(finding)
    assert [item.code for item in finding.not_evaluated] == ["similar_amounts"]
    assert "currencies" in finding.not_evaluated[0].reason


def test_priority_follows_the_number_of_signals():
    assert make_finding().priority == "low"
    assert make_finding(offsets=[0, 1, 2]).priority == "medium"
    assert make_finding(offsets=[0, 1, 2], evidence=["missing", "complete", "complete"]).priority == "high"


def test_a_cycle_that_refers_to_unknown_records_is_rejected_not_skipped():
    facts = {}
    with pytest.raises(ValueError):
        build_finding(Cycle(("a", "b"), ("t1", "t2")), facts, {"a": "A", "b": "B"})
    with pytest.raises(ValueError):
        build_finding(Cycle(("a", "b"), ()), {}, {"a": "A"})
