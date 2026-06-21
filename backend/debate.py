"""Multi-agent debate verification — an ensemble that lifts accuracy on hard claims.

Instead of one model committing to a label, N independent verifier agents judge
the SAME evidence through different lenses, then a judge adjudicates. Two payoffs:

  1. Ensemble accuracy: independent reads catch each other's mistakes.
  2. Disagreement is signal. If the skeptic says "refuted" and the charitable
     reader says "supported", that split is almost the definition of
     "Conflicting Evidence/Cherrypicking" — the class single-pass models miss
     most (they retreat to "Not Enough Evidence"). So the vote spread is a
     built-in detector for our weakest label.

Cost: N lens calls (run concurrently; the rate limiter spaces their starts) + 1
judge call per claim. Used in benchmark mode; the accuracy lift vs single-pass
is measured on AVeriTeC.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from llm import complete_json

# Three independent lenses. Same evidence, deliberately different priors, so
# their agreement/disagreement is informative.
_LENSES = {
    "skeptic": (
        "You are a skeptical fact-checker. You assume a forwarded claim is trying "
        "to manipulate, and you demand strong, direct evidence before calling it "
        "true. Thin or tangential evidence is not enough."
    ),
    "literalist": (
        "You are a literal-minded fact-checker. You judge ONLY what the evidence "
        "literally establishes about the exact wording of the claim — no charitable "
        "interpretation, no benefit of the doubt, but no extra suspicion either."
    ),
    "charitable": (
        "You are a charitable fact-checker. You give the claim its most reasonable "
        "interpretation and check whether, read fairly, the evidence bears it out."
    ),
}

_LABEL_RULES = (
    "Choose exactly one label:\n"
    '- "supported": evidence shows the claim is true.\n'
    '- "refuted": evidence shows the claim is false.\n'
    '- "conflicting": evidence both supports and refutes parts, OR the claim is '
    "technically true but cherry-picks/misleads.\n"
    '- "nei": evidence is genuinely insufficient to decide.\n'
)


def _lens_vote(lens_key: str, claim: str, evidence_block: str, qa_block: str) -> dict:
    system = _LENSES[lens_key] + " You reason only from the evidence. You output only JSON."
    prompt = (
        f'Claim:\n"""{claim}"""\n\n'
        f"Researched answers:\n{qa_block}\n\n"
        f"Evidence (numbered):\n{evidence_block}\n\n"
        f"{_LABEL_RULES}\n"
        'Return ONLY this JSON: {"label": "supported|refuted|conflicting|nei", '
        '"confidence": <0-100 integer>, "reason": "<one sentence>"}'
    )
    try:
        r = complete_json(system, prompt, max_tokens=16384)
        return {"lens": lens_key, "label": str(r.get("label", "")).lower(),
                "confidence": r.get("confidence", 50), "reason": str(r.get("reason", ""))[:200]}
    except Exception as e:
        return {"lens": lens_key, "label": "", "confidence": 0, "reason": f"(error {type(e).__name__})"}


_JUDGE_SYSTEM = (
    "You are the presiding judge over three fact-checkers who examined the same "
    "evidence through different lenses. You weigh their verdicts and the evidence "
    "and deliver the final label. Crucially: if they genuinely split between "
    "'supported' and 'refuted', that usually means the claim is true in a narrow "
    "sense but misleading overall — label it 'conflicting', not 'nei'. You output only JSON."
)


def judge(claim: str, evidence_block: str, votes: list[dict]) -> dict:
    panel = "\n".join(
        f"- {v['lens']}: {v['label'] or 'no-call'} (conf {v['confidence']}) — {v['reason']}"
        for v in votes
    )
    prompt = (
        f'Claim:\n"""{claim}"""\n\n'
        f"Panel verdicts:\n{panel}\n\n"
        f"Evidence (numbered):\n{evidence_block}\n\n"
        f"{_LABEL_RULES}\n"
        "Weigh the panel. A split between supported and refuted => prefer 'conflicting'. "
        "Unanimous => trust it. Mixed with nei => decide on the evidence.\n"
        'Return ONLY this JSON: {"label": "supported|refuted|conflicting|nei", '
        '"confidence": <0-100 integer>, "reason": "<one sentence>", "panel_split": true or false}'
    )
    return complete_json(_JUDGE_SYSTEM, prompt, max_tokens=16384)


def debate_decide(claim: str, loop_result: dict, lenses: tuple[str, ...] = ("skeptic", "literalist", "charitable")) -> dict:
    """Run the lens panel concurrently, then judge. Returns the judge's verdict
    plus the raw panel (so the UI / report can show the disagreement)."""
    qa = loop_result.get("qa") or []
    qa_block = "\n".join(f"- Q: {a.get('q','')}\n  A: {a.get('a','')}" for a in qa) or "(no answers extracted)"
    from agentic import _evidence_block
    ev_block = _evidence_block(loop_result.get("evidence") or [])

    with ThreadPoolExecutor(max_workers=len(lenses)) as ex:
        votes = list(ex.map(lambda L: _lens_vote(L, claim, ev_block, qa_block), lenses))

    labels = [v["label"] for v in votes if v["label"]]
    # Cheap signal we can use even if the judge call fails.
    split = ("supported" in labels and "refuted" in labels)

    # If the panel is unanimous, the judge call adds nothing — skip it (saves a
    # Gemma call on the easy claims, and reserves the judge for real disagreement).
    if len(labels) >= 2 and len(set(labels)) == 1:
        return _result(labels[0], votes, "unanimous panel", split=False, judged=False)

    try:
        v = judge(claim, ev_block, votes)
        final = str(v.get("label", "")).lower()
        out = _result(final, votes, str(v.get("reason", "judge"))[:200],
                      split=bool(v.get("panel_split", split)), judged=True)
        return out
    except Exception:
        # Judge empty -> fall back to a vote rule (split => conflicting).
        if split:
            final = "conflicting"
        elif labels:
            final = max(set(labels), key=labels.count)
        else:
            final = "nei"
        return _result(final, votes, "panel vote (judge unavailable)", split=split, judged=False)


def _result(final: str, votes: list[dict], reason: str, split: bool, judged: bool) -> dict:
    """Attach a STRUCTURAL confidence: the fraction of independent lenses that
    agreed with the final label. Self-reported model confidence is near-useless
    (it says ~100% on everything; ECE ~0.33), so panel agreement — which actually
    tracks correctness — is what product mode should abstain on."""
    valid = [v["label"] for v in votes if v["label"]]
    agree = (sum(1 for L in valid if L == final) / len(valid)) if valid else 0.0
    # 3/3 -> 92, 2/3 -> 73, 1/3 -> 55, 0 -> 40. Monotonic in agreement.
    conf = int(round(40 + 52 * agree))
    return {"label": final, "confidence": conf, "agreement": round(agree, 2),
            "reason": reason, "panel_split": split, "votes": votes, "judged": judged}
