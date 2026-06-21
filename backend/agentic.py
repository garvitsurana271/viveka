"""Bounded agentic multi-hop verification loop — the research-grade core.

Instead of the old single-hop "analyze -> retrieve once -> verify", the agent
runs a loop: read the evidence gathered so far, extract what it answers, decide
whether the claim is settled, and if not choose the most useful next searches —
until the claim is settled or a hard hop budget runs out. This is the technique
that separates strong AVeriTeC systems from "retrieve and guess": follow-up
questions surface the evidence a single query misses, and the hop budget keeps
the whole thing runnable inside Gemma's 15 RPM / 1,500 RPD limits.

Call budget per claim: 1 (analyze, done by the caller) + H planner hops + 1
final verdict, with H <= max_hops. So <= max_hops + 1 calls here.

One core, two decision policies (see `decide`):
  - mode="benchmark": commit to one AVeriTeC label (for scoring).
  - mode="product":   full bilingual verdict with calibrated abstention.

The loop is async (retrieval is I/O-bound and fanned out); callers in a sync
context use asyncio.run.
"""
from __future__ import annotations
import asyncio
import math

import websearch
import wikipedia
import factcheck
import credibility
from llm import complete_json

MAX_HOPS_DEFAULT = 3
EVIDENCE_CAP = 12          # most credible kept; what the model weighs
PER_QUERY_RESULTS = 3

# --- Retrieval dispatch ------------------------------------------------------

async def _run_tool(tool: str, query: str) -> list[dict]:
    tool = (tool or "web").lower()
    try:
        if tool == "wikipedia":
            return await wikipedia.search(query, max_results=2)
        if tool == "factcheck":
            return await factcheck.search(query, max_results=3)
        return await websearch.search(query, max_results=PER_QUERY_RESULTS)
    except Exception:
        return []


async def gather(plans: list[dict]) -> list[dict]:
    """plans: [{tool, query}, ...] -> deduped, credibility-tagged sources."""
    plans = [p for p in (plans or []) if p.get("query")][:3]
    if not plans:
        return []
    results = await asyncio.gather(*[_run_tool(p.get("tool", "web"), p["query"]) for p in plans],
                                   return_exceptions=True)
    out: list[dict] = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)
    return out


def _merge(existing: list[dict], new: list[dict]) -> list[dict]:
    """Add genuinely-new sources, tag credibility, keep the most credible EVIDENCE_CAP."""
    seen = {(s.get("org"), s.get("url")) for s in existing}
    for s in new:
        key = (s.get("org"), s.get("url"))
        if key in seen or not s.get("note"):
            continue
        seen.add(key)
        label, score = credibility.tier_source(s)
        s["tier"] = label
        s["_score"] = score
        existing.append(s)
    existing.sort(key=lambda x: x.get("_score", 1), reverse=True)
    return existing[:EVIDENCE_CAP]


def _evidence_block(evidence: list[dict]) -> str:
    if not evidence:
        return "(nothing retrieved yet)"
    return "\n".join(
        f"[{i + 1}] {e.get('org','?')} ({e.get('tier','web')}): {e.get('note','')} ({e.get('url','')})"
        for i, e in enumerate(evidence)
    )


# --- The hop planner: read evidence, extract answers, decide next ------------

_PLANNER_SYSTEM = (
    "You are a fact-checking research agent. Given a claim, the questions that "
    "would settle it, and the evidence gathered so far, you (1) extract what the "
    "evidence answers, (2) decide whether you can now reach a confident verdict, "
    "and (3) if not, choose the most useful next searches. You never invent facts. "
    "You output only JSON."
)


def _planner_prompt(claim, questions, evidence, hops_used, max_hops) -> str:
    qs = "\n".join(f"- {q}" for q in questions) or "- Is the claim's main assertion true?"
    near_end = hops_used >= max_hops - 1
    return f'''Claim:
"""{claim}"""

Questions to settle:
{qs}

Evidence gathered so far (numbered):
{_evidence_block(evidence)}

You have used {hops_used} of {max_hops} search hops.{" This is your LAST hop — prefer to conclude." if near_end else ""}

Return ONLY this JSON:
{{
  "answers": [{{"q": "<question>", "a": "<answer from the evidence, or 'not yet established'>", "src": "<evidence number(s) or org>"}}],
  "enough": true or false,
  "missing": "<the single most important fact still missing, or ''>",
  "next": [{{"tool": "web | wikipedia | factcheck", "query": "<short search query>", "why": "<what it resolves>"}}]
}}

Rules:
- Answer each question ONLY from the evidence. If unanswered, say "not yet established".
- Set "enough": true as soon as the evidence clearly supports, refutes, or shows the claim is misleading/cherry-picked — do not over-search.
- If this is your last hop, set "enough": true and rule on what you have.
- "next": at most 2 queries aimed at the biggest gap, and ONLY if "enough" is false. Use factcheck to see if a claim was already debunked, wikipedia for stable facts, web for current/local/specific facts.
'''


# --- P5: HyDE-FC — imagine the evidence, search for it (incl. the conflict angle) ---

_HYDE_SYSTEM = (
    "You are a fact-checking research assistant. For a claim you imagine what real "
    "evidence might say, for AND against, and turn that into precise web-search "
    "queries — including one aimed at whether the claim is true-but-misleading / "
    "cherry-picked. You output only JSON."
)


def hyde_plan(claim: str) -> list[dict]:
    """One Gemma call: generate queries that hunt for confirming, refuting, AND
    conflicting/cherry-picking evidence. The conflict query is what lifts the weak
    Conflicting class — it actively looks for the missing-context angle."""
    prompt = (
        f'Claim:\n"""{claim}"""\n\n'
        "Imagine the strongest real evidence for and against this, then give search queries:\n"
        "- confirm: a query to find evidence the claim is TRUE\n"
        "- refute: a query to find evidence it is FALSE\n"
        "- conflict: a query to find whether it is TRUE BUT MISLEADING / missing key context\n\n"
        'Return ONLY this JSON: {"confirm": "<query>", "refute": "<query>", "conflict": "<query>"}'
    )
    try:
        r = complete_json(_HYDE_SYSTEM, prompt, max_tokens=8192)
    except Exception:
        return []
    out = []
    for k in ("confirm", "refute", "conflict"):
        q = str(r.get(k, "")).strip()
        if q:
            out.append({"tool": "web", "query": q})
    return out


async def _maybe_enrich(evidence: list[dict], claim: str, questions: list[str], full_doc: bool) -> list[dict]:
    """P1: replace the top sources' snippets with full-article windows."""
    if not full_doc or not evidence:
        return evidence
    import fetch
    relevance = (claim + " " + " ".join(questions or [])).strip()
    return await fetch.enrich(evidence, relevance)


async def run_loop(claim: str, questions: list[str], queries: list[dict],
                   max_hops: int = MAX_HOPS_DEFAULT, full_doc: bool = False,
                   hyde: bool = False) -> dict:
    """Returns {evidence, qa, hops, trace}. `queries` is the initial plan from
    analyze: a list of {tool, query} (or bare strings -> web). full_doc=True (P1)
    fetches the top sources in full; hyde=True (P5) also searches imagined-evidence
    queries, including a conflict/cherry-picking query."""
    init = [q if isinstance(q, dict) else {"tool": "web", "query": q} for q in (queries or [])]
    if hyde:
        init = (await asyncio.to_thread(hyde_plan, claim)) + init
    evidence = _merge([], await gather(init))
    evidence = await _maybe_enrich(evidence, claim, questions, full_doc)
    qa: list[dict] = []
    trace: list[dict] = [{"hop": 0, "action": "initial", "queries": [p.get("query") for p in init],
                          "n_evidence": len(evidence)}]

    hops = 0
    while hops < max_hops:
        try:
            plan = await asyncio.to_thread(
                complete_json, _PLANNER_SYSTEM,
                _planner_prompt(claim, questions, evidence, hops, max_hops),
                max_tokens=16384,
            )
        except Exception:
            break  # planner empty -> stop looping, decide on what we have
        if isinstance(plan.get("answers"), list) and plan["answers"]:
            qa = plan["answers"]  # latest reading supersedes (it sees all evidence)
        nxt = plan.get("next") or []
        trace.append({"hop": hops + 1, "enough": bool(plan.get("enough")),
                      "missing": plan.get("missing", ""),
                      "next": [p.get("query") for p in nxt if isinstance(p, dict)]})
        if plan.get("enough") or not nxt:
            break
        before = len(evidence)
        evidence = _merge(evidence, await gather(nxt))
        evidence = await _maybe_enrich(evidence, claim, questions, full_doc)
        hops += 1
        if len(evidence) == before:
            break  # search added nothing new -> stop burning hops

    return {"evidence": evidence, "qa": qa, "hops": hops, "trace": trace}


# --- Benchmark decision policy: commit to one AVeriTeC label -----------------

_DECIDE_SYSTEM = (
    "You are a rigorous fact-checking adjudicator. Given a claim and the evidence "
    "gathered for it, you commit to exactly one verdict label. You reason only from "
    "the evidence. You output only JSON."
)

_BENCH_LABEL_RULES = (
    "Choose exactly one label:\n"
    '- "supported": the evidence shows the claim is true.\n'
    '- "refuted": the evidence shows the claim is false.\n'
    '- "conflicting": the evidence both supports and refutes parts of it, OR the '
    "claim is technically true but cherry-picks / misleads (a real but distorted basis).\n"
    '- "nei": the evidence is genuinely insufficient to decide.\n'
)


def decide_benchmark(claim: str, loop_result: dict, shots: str = "") -> dict:
    """One committed AVeriTeC label over the loop's accumulated evidence + QA.
    `shots` is an optional pre-built few-shot exemplar block."""
    qa = loop_result.get("qa") or []
    qa_txt = "\n".join(f"- Q: {a.get('q','')}\n  A: {a.get('a','')}" for a in qa) or "(no answers extracted)"
    ev_txt = _evidence_block(loop_result.get("evidence") or [])
    if shots:
        shots = shots + "\n\n---\n\n"
    prompt = (
        f"{shots}"
        f'Claim:\n"""{claim}"""\n\n'
        f"Researched answers:\n{qa_txt}\n\n"
        f"Evidence (numbered):\n{ev_txt}\n\n"
        f"{_BENCH_LABEL_RULES}\n"
        'Return ONLY this JSON: {"label": "supported|refuted|conflicting|nei", '
        '"confidence": <0-100 integer>, "reason": "<one sentence>"}'
    )
    return complete_json(_DECIDE_SYSTEM, prompt, max_tokens=16384)


# --- P2: Likert-softmax veracity (graded confidence + tunable NEI threshold) --

_LIKERT_SYSTEM = (
    "You are a rigorous fact-checking adjudicator. Given a claim and its evidence, "
    "you rate how strongly the evidence fits EACH of four verdicts, on a 1-5 scale "
    "(1 = not at all, 5 = strongly). You reason only from the evidence. You output only JSON."
)

_LABELS4 = ("supported", "refuted", "conflicting", "nei")
# Decision uses raw probabilities (temp=1); the reported confidence uses a softer
# temperature so a dominant Likert "5" doesn't read as 95% — this lowers ECE
# without changing the argmax label, so the macro-F1 is unaffected.
_CONF_TEMP = 2.2


def _softmax(xs: list[float], temp: float = 1.0) -> list[float]:
    m = max(xs)
    exps = [math.exp((x - m) / temp) for x in xs]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def decide_likert(claim: str, loop_result: dict, nei_margin: float = 0.12,
                  shots: str = "", samples: int = 1) -> dict:
    """Rate all four verdicts 1-5, softmax to probabilities. The label is the
    argmax, EXCEPT "nei" is only chosen when it beats the best decisive label by
    `nei_margin` — that's the tunable knob against over-abstention. Confidence is
    the winning probability (graded, not the flat ~98% self-report). `shots` is an
    optional pre-built few-shot exemplar block. `samples`>1 enables SELF-CONSISTENCY:
    rate the claim several times at higher temperature and average the scores,
    which damps the per-call noise in Gemma's ratings."""
    qa = loop_result.get("qa") or []
    qa_txt = "\n".join(f"- Q: {a.get('q','')}\n  A: {a.get('a','')}" for a in qa) or "(no answers extracted)"
    ev_txt = _evidence_block(loop_result.get("evidence") or [])
    if shots:
        shots = shots + "\n\n---\n\n"
    prompt = (
        f"{shots}"
        f'Claim:\n"""{claim}"""\n\n'
        f"Researched answers:\n{qa_txt}\n\n"
        f"Evidence (numbered):\n{ev_txt}\n\n"
        "Rate how well the evidence supports EACH verdict (1-5):\n"
        '- "supported": evidence shows the claim is true.\n'
        '- "refuted": evidence shows it is false.\n'
        '- "conflicting": evidence both supports and refutes, or it is true-but-misleading/cherry-picked.\n'
        '- "nei": the evidence is genuinely insufficient to decide.\n\n'
        'Return ONLY this JSON: {"supported": <1-5>, "refuted": <1-5>, '
        '"conflicting": <1-5>, "nei": <1-5>, "reason": "<one sentence>"}'
    )
    # Self-consistency: sample `samples` times (>1 at higher temperature for
    # diversity) and average the per-label scores. One sample = the original path.
    def _one(temp):
        r = complete_json(_LIKERT_SYSTEM, prompt, max_tokens=16384, temperature=temp)
        out = []
        for k in _LABELS4:
            try:
                out.append(max(1.0, min(5.0, float(r.get(k, 1)))))
            except Exception:
                out.append(1.0)
        return out, str(r.get("reason", ""))

    samples = max(1, samples)
    runs, reason = [], ""
    for n in range(samples):
        try:
            sc, rsn = _one(None if samples == 1 else 0.7)
            runs.append(sc)
            reason = reason or rsn
        except Exception:
            continue
    if not runs:
        return {"label": "nei", "confidence": 0, "probs": {}, "reason": "(no samples)"}
    raw = [sum(s[i] for s in runs) / len(runs) for i in range(4)]   # averaged scores
    probs = _softmax(raw)                       # decision
    ranked = sorted(range(4), key=lambda i: -probs[i])
    top = ranked[0]
    if _LABELS4[top] == "nei":
        best_decisive = max((i for i in range(4) if _LABELS4[i] != "nei"), key=lambda i: probs[i])
        if probs[top] - probs[best_decisive] < nei_margin:
            top = best_decisive
    conf = _softmax(raw, temp=_CONF_TEMP)       # calibrated confidence (softer)
    return {
        "label": _LABELS4[top],
        "confidence": int(round(conf[top] * 100)),
        "probs": {_LABELS4[i]: round(probs[i], 3) for i in range(4)},
        "reason": reason[:300],
    }
