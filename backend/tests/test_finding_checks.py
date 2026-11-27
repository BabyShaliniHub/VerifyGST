from datetime import date, timedelta

from app.analysis.findings import CHECKS, TransactionFact, build_finding, check_results
from app.graph.cycles import Cycle


def finding(*, evidence=None, amounts=None, offsets=None, currencies=None, references=None):
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


def results(f):
    return {r.code: r.result for r in check_results(f)}


def test_a_quiet_finding_lists_every_check_as_not_triggered():
    quiet = results(finding())
    assert quiet == {code: "not_triggered" for code, _ in CHECKS}


def test_a_triggered_check_is_marked_and_the_others_are_not():
    only_timing = results(finding(offsets=[0, 1, 2]))
    assert only_timing["tight_timing"] == "triggered"
    assert [state for code, state in only_timing.items() if code != "tight_timing"] == ["not_triggered"] * 3


def test_a_check_that_could_not_run_is_not_evaluated_and_never_not_triggered():
    mixed = results(finding(currencies=["INR", "INR", "USD"]))
    assert mixed["similar_amounts"] == "not_evaluated"


def test_the_check_titles_match_the_titles_of_the_signals_they_describe():
    loud = finding(
        evidence=["missing", "complete", "complete"],
        references=["SAME", "SAME", "REF-2"],
        amounts=[1_000_000, 1_000_000, 1_000_000],
        offsets=[0, 1, 2],
    )
    titles = {signal.code: signal.title for signal in loud.signals}
    assert set(titles) == {code for code, _ in CHECKS}
    for code, title in CHECKS:
        assert titles[code] == title


def test_the_results_follow_the_fixed_check_order():
    assert [r.code for r in check_results(finding())] == [code for code, _ in CHECKS]
