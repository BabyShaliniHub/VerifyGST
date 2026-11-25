import itertools
from decimal import Decimal

from app.graph.sync import to_minor_units
from app.seed.demo_data import COMPANIES, TRANSACTIONS, stable_id
from app.services.invoice_authentication.normalization import normalize_domain, normalize_name

EVIDENCE_LEVELS = {"complete", "partial", "missing"}


def test_the_seed_has_the_demo_companies_and_transactions():
    assert len(COMPANIES) == 8
    assert len(TRANSACTIONS) == 9


def test_company_keys_names_and_domains_are_unique_and_valid():
    assert len({c.key for c in COMPANIES}) == len(COMPANIES)
    assert len({c.name for c in COMPANIES}) == len(COMPANIES)
    assert len({c.domain for c in COMPANIES}) == len(COMPANIES)
    for company in COMPANIES:
        assert normalize_name(company.name) == company.name
        assert normalize_domain(company.domain) == company.domain
        assert company.domain.endswith(".example")


def test_every_transaction_joins_two_different_known_companies():
    known = {c.key for c in COMPANIES}
    assert len({t.key for t in TRANSACTIONS}) == len(TRANSACTIONS)
    for transaction in TRANSACTIONS:
        assert transaction.seller_key in known
        assert transaction.buyer_key in known
        assert transaction.seller_key != transaction.buyer_key


def test_amounts_are_positive_with_two_decimals_and_evidence_levels_are_valid():
    for transaction in TRANSACTIONS:
        assert transaction.amount > 0
        assert transaction.amount == transaction.amount.quantize(Decimal("0.01"))
        assert transaction.evidence_level in EVIDENCE_LEVELS


def test_ids_are_stable_and_distinct():
    # If these fail, the id derivation changed and previously seeded rows would be duplicated.
    assert str(stable_id("company", "C1")) == "0bf5e16e-1010-5890-a609-4d3e2fc67842"
    assert str(stable_id("transaction", "T1")) == "c1d6f155-a732-5306-bd1c-daa6b35b664f"
    ids = [stable_id("company", c.key) for c in COMPANIES] + [
        stable_id("transaction", t.key) for t in TRANSACTIONS
    ]
    assert len(set(ids)) == len(ids)
    assert stable_id("company", "C1") != stable_id("transaction", "C1")


def test_the_graph_has_exactly_the_two_three_company_cycles():
    edges = {(t.seller_key, t.buyer_key) for t in TRANSACTIONS}
    keys = [c.key for c in COMPANIES]
    cycles = set()
    for a, b, c in itertools.permutations(keys, 3):
        if (a, b) in edges and (b, c) in edges and (c, a) in edges:
            cycles.add(frozenset((a, b, c)))
    assert cycles == {frozenset({"C1", "C2", "C3"}), frozenset({"C4", "C5", "C6"})}


def test_only_the_suspicious_cycle_repeats_an_invoice_reference():
    references = [t.invoice_reference for t in TRANSACTIONS]
    repeated = {r for r in references if references.count(r) > 1}
    assert repeated == {"INV-D-202"}
    assert {t.key for t in TRANSACTIONS if t.invoice_reference == "INV-D-202"} == {"T5", "T6"}


def test_money_converts_to_whole_paise():
    assert to_minor_units(Decimal("4790000.00")) == 479000000
    assert to_minor_units(Decimal("1250000.00")) == 125000000
    assert to_minor_units(Decimal("0.07")) == 7
