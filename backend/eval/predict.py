"""Two predictors that turn an AVeriTeC claim into a committed label.

Track A — gold-evidence reasoning: feed the claim plus AVeriTeC's own gold
questions+answers, ask Gemma for the label. Isolates *veracity reasoning*
(aggregating evidence) from retrieval. One Gemma call per claim.

Track B — live end-to-end: run Viveka's real pipeline (analyze -> multi-source
retrieve -> verify) on the bare claim and map its verdict. Tests the whole
deployed system, retrieval included.

Both run in "benchmark/commit" mode: they pick one of the four AVeriTeC labels
and never route to a human (abstention is a product behaviour, scored
separately). NEI is only emitted when the model genuinely judges the evidence
insufficient.
"""
from __future__ import annotations
import os
import sys
import asyncio

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import llm_cache              # noqa: E402
from mapping import normalise_label, product_to_averitec, NEI  # noqa: E402

# --- Track A: gold-evidence veracity reasoning -------------------------------

_GOLD_SYSTEM = (
    "You are a rigorous fact-checking adjudicator. Given a claim and a set of "
    "researched questions with their evidence-based answers, you decide whether "
    "the evidence supports, refutes, conflicts on, or is insufficient for the "
    "claim. You reason only from the evidence given. You output only JSON."
)

_LABEL_RULES = (
    "Choose exactly one label:\n"
    '- "supported": the evidence, taken together, shows the claim is true.\n'
    '- "refuted": the evidence shows the claim is false.\n'
    '- "conflicting": the evidence both supports and refutes parts of it, or the '
    "claim is technically true but cherry-picks/misleads.\n"
    '- "nei": the evidence is genuinely insufficient to decide either way.\n'
)


def _format_evidence(entry: dict) -> str:
    out = []
    for i, q in enumerate(entry.get("questions") or [], 1):
        ans = []
        for a in q.get("answers") or []:
            t = (a.get("answer") or "").strip()
            if a.get("answer_type") == "Boolean" and a.get("boolean_explanation"):
                t = f"{t} — {a['boolean_explanation'].strip()}"
            if t:
                ans.append(t)
        a_txt = " / ".join(ans) if ans else "(no answer found)"
        out.append(f"Q{i}: {q.get('question','').strip()}\nA{i}: {a_txt[:600]}")
    return "\n".join(out) if out else "(no evidence provided)"


def _build_shots(claim: str, mode: str) -> str:
    """mode: 'none' | 'static' | 'dynamic' -> a few-shot exemplar block."""
    if mode in ("none", "", None):
        return ""
    import fewshot
    b = fewshot.dynamic_block(claim) if mode == "dynamic" else fewshot.block()
    return b or ""


def _gold_qa(entry: dict) -> list[dict]:
    qa = []
    for q in entry.get("questions") or []:
        a = ""
        for ans in q.get("answers") or []:
            a = (ans.get("answer") or "").strip()
            if a:
                break
        qa.append({"q": q.get("question", ""), "a": a or "(no answer found)"})
    return qa


def predict_gold(entry: dict, fewshot_mode: str = "none", likert: bool = False,
                 samples: int = 1) -> dict:
    """Reason over gold evidence. fewshot_mode none/static/dynamic (P3);
    likert=True uses the P2 Likert-softmax decision; samples>1 = self-consistency."""
    claim = entry.get("claim", "")
    shots = _build_shots(claim, fewshot_mode)

    if likert:  # P2 over gold evidence
        import agentic
        loop = {"evidence": [], "qa": _gold_qa(entry)}
        try:
            v = agentic.decide_likert(claim, loop, shots=shots, samples=samples)
        except Exception as e:
            return {"pred": NEI, "confidence": 0, "reason": f"(likert error: {type(e).__name__})", "error": True}
        return {"pred": normalise_label(v.get("label")), "confidence": _int(v.get("confidence"), 50),
                "probs": v.get("probs"), "reason": str(v.get("reason", ""))[:300], "error": False}

    evidence = _format_evidence(entry)
    pre = (shots + "\n\n---\n\n") if shots else ""
    prompt = (
        f"{pre}"
        f'Claim:\n"""{claim}"""\n\n'
        f"Researched evidence:\n{evidence}\n\n"
        f"{_LABEL_RULES}\n"
        'Return ONLY this JSON: {"label": "supported|refuted|conflicting|nei", '
        '"confidence": <0-100 integer>, "reason": "<one sentence>"}'
    )
    # Gemma 'thinks' before answering and that thinking counts against the output
    # budget; the fix is a generous ceiling, not a retry (gemma-4-31b-it allows 32768).
    try:
        r = llm_cache.cached_complete_json(_GOLD_SYSTEM, prompt, max_tokens=32768)
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "reason": f"(error: {type(e).__name__})", "error": True}
    return {
        "pred": normalise_label(r.get("label")),
        "confidence": _int(r.get("confidence"), 50),
        "reason": str(r.get("reason", ""))[:300],
        "error": False,
    }


# --- Track B: live end-to-end pipeline (current engine baseline) -------------

def predict_live(claim: str) -> dict:
    """Run the real analyze -> retrieve -> verify pipeline and commit to a label.
    Maps the engine's *raw* verdict (before product-mode abstention) so the
    number reflects what the engine actually concluded; abstention is recorded
    separately."""
    import analyze
    import verify
    import engine
    try:
        d = analyze.analyze(claim)
    except Exception:
        d = engine._basic_analysis(claim)
    domain = d.get("domain", "general")
    claims = d.get("claims") or [claim]
    questions = d.get("questions") or []
    queries = d.get("queries") or [claim]
    try:
        sources = asyncio.run(engine._retrieve(queries, domain))
    except Exception:
        sources = []
    try:
        r = verify.verify(claim, claims, questions, sources, domain)
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "abstained": True, "n_sources": len(sources),
                "reason": f"(verify error: {type(e).__name__})", "error": True}
    raw_verdict = str(r.get("verdict", "human")).lower()
    conf = _int(r.get("confidence"), 50)
    suff = bool(r.get("evidence_sufficient", True))
    pred = product_to_averitec(raw_verdict)
    # "Would product mode have abstained?" — for the abstention-cost report.
    abstained = (raw_verdict in ("human",)) or (not suff)
    return {
        "pred": pred, "confidence": conf, "abstained": abstained,
        "n_sources": len(sources), "reason": str(r.get("weigh_note", ""))[:300],
        "raw_verdict": raw_verdict, "error": False,
    }


# --- Track B2: multi-agent debate over GOLD evidence (clean decision A/B) -----

def predict_gold_debate(entry: dict) -> dict:
    """Same gold evidence as predict_gold, but the decision is made by the
    3-lens debate panel + judge instead of a single pass. Isolates the value of
    the debate mechanism (evidence held constant)."""
    import debate
    claim = entry.get("claim", "")
    qa_list = []
    for q in entry.get("questions") or []:
        a = ""
        for ans in q.get("answers") or []:
            a = (ans.get("answer") or "").strip()
            if a:
                break
        qa_list.append({"q": q.get("question", ""), "a": a or "(no answer found)"})
    loop = {"evidence": [], "qa": qa_list}
    try:
        v = debate.debate_decide(claim, loop)
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "split": False,
                "reason": f"(debate error: {type(e).__name__})", "error": True}
    return {
        "pred": normalise_label(v.get("label")),
        "confidence": _int(v.get("confidence"), 50),
        "agreement": v.get("agreement"),
        "split": bool(v.get("panel_split")),
        "reason": str(v.get("reason", ""))[:300],
        "error": False,
    }


# --- Track C: bounded agentic multi-hop loop (Phase 2) -----------------------

def predict_agentic(claim: str, max_hops: int = 3, fewshot_mode: str = "none",
                    likert: bool = False, fulldoc: bool = False, hyde: bool = False) -> dict:
    """analyze -> bounded agentic retrieval loop -> committed AVeriTeC label.
    Toggles: fulldoc=P1 (read full articles), likert=P2, fewshot_mode=P3, hyde=P5."""
    import analyze
    import agentic
    import engine
    try:
        d = analyze.analyze(claim)
    except Exception:
        d = engine._basic_analysis(claim)
    questions = d.get("questions") or []
    queries = d.get("queries") or [claim]
    try:
        loop = asyncio.run(agentic.run_loop(claim, questions, queries, max_hops=max_hops,
                                            full_doc=fulldoc, hyde=hyde))
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "hops": 0, "n_sources": 0,
                "reason": f"(loop error: {type(e).__name__})", "error": True}
    shots = _build_shots(claim, fewshot_mode)
    try:
        if likert:
            r = agentic.decide_likert(claim, loop, shots=shots)
        else:
            r = agentic.decide_benchmark(claim, loop, shots=shots)
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "hops": loop.get("hops", 0),
                "n_sources": len(loop.get("evidence", [])),
                "reason": f"(decide error: {type(e).__name__})", "error": True}
    n_full = sum(1 for s in loop.get("evidence", []) if s.get("full_doc"))
    return {
        "pred": normalise_label(r.get("label")),
        "confidence": _int(r.get("confidence"), 50),
        "hops": loop.get("hops", 0),
        "n_sources": len(loop.get("evidence", [])),
        "n_fulldoc": n_full,
        "reason": str(r.get("reason", ""))[:300],
        "error": False,
    }


# --- Track D: agentic loop + multi-agent debate decision (the moat) ----------

def predict_debate(claim: str, max_hops: int = 3) -> dict:
    """analyze -> agentic loop -> 3-lens debate + judge -> committed label."""
    import analyze
    import agentic
    import debate
    import engine
    try:
        d = analyze.analyze(claim)
    except Exception:
        d = engine._basic_analysis(claim)
    questions = d.get("questions") or []
    queries = d.get("queries") or [claim]
    try:
        loop = asyncio.run(agentic.run_loop(claim, questions, queries, max_hops=max_hops))
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "hops": 0, "n_sources": 0, "split": False,
                "reason": f"(loop error: {type(e).__name__})", "error": True}
    try:
        v = debate.debate_decide(claim, loop)
    except Exception as e:
        return {"pred": NEI, "confidence": 0, "hops": loop.get("hops", 0),
                "n_sources": len(loop.get("evidence", [])), "split": False,
                "reason": f"(debate error: {type(e).__name__})", "error": True}
    return {
        "pred": normalise_label(v.get("label")),
        "confidence": _int(v.get("confidence"), 50),
        "agreement": v.get("agreement"),
        "hops": loop.get("hops", 0),
        "n_sources": len(loop.get("evidence", [])),
        "split": bool(v.get("panel_split")),
        "reason": str(v.get("reason", ""))[:300],
        "error": False,
    }


def _int(v, default):
    try:
        return max(0, min(100, int(v)))
    except Exception:
        return default
