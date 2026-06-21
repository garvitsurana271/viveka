"""Few-shot exemplars drawn from the AVeriTeC train split.

The dev baseline shows the model is strong on Supported/Refuted but collapses on
"Conflicting Evidence/Cherrypicking" — it retreats to "Not Enough Evidence"
instead of recognising a claim that is technically true but misleading. Few-shot
exemplars teach that boundary: each shows a claim, a one-line evidence gist, the
correct label, and why. We hand-pick clear cases (especially Conflicting vs NEI)
rather than sampling at random, so the demonstrations actually disambiguate.

Pure data work — no API calls. Loaded once and cached.
"""
from __future__ import annotations
import os
import re
import json

_TRAIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval", "data", "train.json")
_train_cache: list[dict] | None = None
_bm25 = None
_bm25_entries: list[dict] | None = None

# Map dataset label -> the short key the prompts ask the model to emit.
_LABEL_KEY = {
    "Supported": "supported",
    "Refuted": "refuted",
    "Conflicting Evidence/Cherrypicking": "conflicting",
    "Not Enough Evidence": "nei",
}


def _load() -> list[dict]:
    global _train_cache
    if _train_cache is None:
        try:
            with open(_TRAIN_PATH, encoding="utf-8") as f:
                _train_cache = json.load(f)
        except Exception:
            _train_cache = []
    return _train_cache


def _gist(entry: dict, max_q: int = 2) -> str:
    """A compact evidence gist: the first couple of Q/A pairs, trimmed."""
    bits = []
    for q in (entry.get("questions") or [])[:max_q]:
        ans = ""
        for a in q.get("answers") or []:
            ans = (a.get("answer") or "").strip()
            if ans:
                break
        if ans:
            bits.append(f"{q.get('question','').strip()} -> {ans[:140]}")
    return " ; ".join(bits)


def _pick(label: str, n: int) -> list[dict]:
    """Pick n train entries for a label that have a usable evidence gist and a
    short justification, deterministically (dataset order)."""
    out = []
    for e in _load():
        if e.get("label") != label:
            continue
        if not _gist(e) or not (e.get("justification") or "").strip():
            continue
        out.append(e)
        if len(out) >= n:
            break
    return out


def block(per_class: int = 1, emphasise_conflicting: int = 2) -> str:
    """A formatted few-shot block. By default one exemplar per class, with extra
    Conflicting examples (the weak boundary). Returns '' if train is unavailable."""
    plan = [
        ("Supported", per_class),
        ("Refuted", per_class),
        ("Conflicting Evidence/Cherrypicking", max(per_class, emphasise_conflicting)),
        ("Not Enough Evidence", per_class),
    ]
    lines = []
    for label, n in plan:
        for e in _pick(label, n):
            lines.append(
                f'Claim: "{e["claim"][:200]}"\n'
                f"Evidence: {_gist(e)}\n"
                f'Correct label: {_LABEL_KEY[label]} — {(e.get("justification") or "").strip()[:200]}'
            )
    if not lines:
        return ""
    return ("Worked examples (study how the label follows from the evidence, "
            "especially 'conflicting' = technically true but cherry-picked/misleading):\n\n"
            + "\n\n".join(lines))


def _exemplar(e: dict) -> str:
    label = e.get("label", "")
    return (f'Claim: "{e["claim"][:200]}"\n'
            f"Evidence: {_gist(e)}\n"
            f'Correct label: {_LABEL_KEY.get(label, label)} — {(e.get("justification") or "").strip()[:200]}')


def _ensure_bm25():
    """Lazily build a BM25 index over train-claim tokens (claims with usable
    evidence + justification only). Built once, cached."""
    global _bm25, _bm25_entries
    if _bm25 is None:
        from rank_bm25 import BM25Okapi
        entries = [e for e in _load() if _gist(e) and (e.get("justification") or "").strip()]
        corpus = [re.findall(r"\w+", e.get("claim", "").lower()) for e in entries]
        _bm25 = BM25Okapi(corpus) if corpus else None
        _bm25_entries = entries
    return _bm25, _bm25_entries


def dynamic_block(claim: str, k: int = 5) -> str:
    """P3: the k train claims most lexically similar to THIS claim, as few-shot
    exemplars. Retrieval-based selection (the research-endorsed fix) instead of
    the same static set for every claim."""
    bm25, entries = _ensure_bm25()
    if not bm25 or not entries:
        return ""
    toks = re.findall(r"\w+", (claim or "").lower())
    if not toks:
        return ""
    scores = bm25.get_scores(toks)
    top = sorted(range(len(entries)), key=lambda i: -scores[i])[:k]
    lines = [_exemplar(entries[i]) for i in top if scores[i] > 0]
    if not lines:
        return ""
    return ("Closely related checked claims (use them to calibrate this verdict; "
            "note especially when a claim is technically true but cherry-picked):\n\n"
            + "\n\n".join(lines))


if __name__ == "__main__":  # quick manual check
    print("STATIC block:\n", block()[:400])
    print("\n\nDYNAMIC block for a mask claim:\n",
          dynamic_block("Wearing face masks stops the spread of COVID-19")[:600])
