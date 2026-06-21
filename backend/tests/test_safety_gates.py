"""Pinning tests for Viveka's safety gates. Deterministic, no Gemma calls.

These answer the question "how do you know the abstention and corroboration gates
actually fire?" They pin the behaviour the Responsible-AI story depends on:
  - a decisive verdict on a high-stakes (health/communal/disaster) claim is forced
    to human review unless an authoritative source corroborates it;
  - the model's own evidence-sufficiency self-check is honoured;
  - the negation guard catches a polarity flip without rejecting legitimate matches;
  - curated seeds never expire; VIVEKA_NO_LEARN disables server-side learning.

Run:  cd backend && .venv/Scripts/python -m pytest tests/ -q
  or:  cd backend && .venv/Scripts/python tests/test_safety_gates.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine
import memory

DECISIVE = {"verdict": "false", "confidence": 88, "evidence_sufficient": True,
            "_calibrated": True, "meaning_en": "x", "weigh_note": "y"}
AUTH = [{"org": "WHO", "note": "no evidence", "tier": "authoritative"}]
OPEN = [{"org": "randomblog.example", "note": "claims it is true", "tier": "open"}]
FACTCHECK = [{"org": "PIB Fact Check", "note": "rated false", "is_factcheck": True}]


def test_highstakes_gate_forces_human_without_authoritative_source():
    out = engine._assemble(dict(DECISIVE), ["A health cure claim"], OPEN, "health")
    assert out["verdict"] == "human", "health + decisive + open-web only must route to human"


def test_highstakes_gate_allows_decisive_with_authoritative_source():
    out = engine._assemble(dict(DECISIVE), ["A health cure claim"], AUTH, "health")
    assert out["verdict"] == "false", "an authoritative source should let the decisive verdict stand"


def test_highstakes_gate_allows_decisive_with_factcheck_source():
    out = engine._assemble(dict(DECISIVE), ["A claim"], FACTCHECK, "communal")
    assert out["verdict"] == "false", "a published fact-check should corroborate a decisive verdict"


def test_gate_does_not_fire_for_low_stakes_domain():
    out = engine._assemble(dict(DECISIVE), ["A trivia claim"], OPEN, "general")
    assert out["verdict"] == "false", "low-stakes domains do not require an authoritative source"


def test_evidence_insufficient_self_check_routes_to_human():
    r = dict(DECISIVE); r["evidence_sufficient"] = False
    out = engine._assemble(r, ["A claim"], AUTH, "general")
    assert out["verdict"] == "human", "the model's own 'evidence insufficient' must abstain"


def test_negation_guard_detects_a_polarity_flip():
    assert memory._claim_negation_flip(
        "garlic cures covid", "garlic does not cure covid") is True


def test_negation_guard_ignores_identical_polarity():
    assert memory._claim_negation_flip(
        "garlic cures covid", "garlic cures the coronavirus") is False


def test_negation_guard_does_not_reject_the_garlic_seed():
    # Regression: a generic 'no' ('no need for hospital') must NOT trigger a flip.
    seed = "Eating raw garlic cures coronavirus, doctors confirm it, no need for hospital."
    query = "Doctors say eating raw garlic cures the coronavirus."
    assert memory._claim_negation_flip(query, seed) is False


def test_curated_seeds_never_expire():
    assert memory._expired({"id": "seed3", "ts": 0}) is False


def test_no_learn_flag_disables_server_side_learning():
    os.environ["VIVEKA_NO_LEARN"] = "1"
    try:
        before = len(memory._store)
        memory.remember("a brand new learnable finance rumour about a fake lottery",
                        {"verdict": "false", "domain": "finance"})
        assert len(memory._store) == before, "VIVEKA_NO_LEARN must persist nothing"
    finally:
        del os.environ["VIVEKA_NO_LEARN"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
