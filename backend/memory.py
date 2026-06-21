"""Antibody DB — semantic memory of checked rumors (claim-matching).

A new forward is embedded and compared (cosine) against everything Viveka has
seen. A close match returns the stored verdict instantly — no LLM call, no
rate-limit cost — and attacks the latency that makes human tiplines useless.
Every novel live check is remembered, so the system builds immunity over time.

Embeddings via the free gemini-embedding-001 (the key already allows it). With
no key, it degrades to fuzzy text matching so seeded rumors are still recognised.
"""
from __future__ import annotations
import json
import os
import math
import time
import difflib
import threading
import httpx
import config

# A cached verdict can go STALE — a claim false today can be true next month
# ("RBI is withdrawing the note", "there's a flood in X right now"). So LEARNED
# entries expire by domain and force a fresh re-check; the more time-sensitive the
# domain, the shorter the life. Curated seeds are timeless myths and never expire.
TTL_DAYS = {"disaster": 1, "communal": 2, "finance": 3, "general": 7,
            "product": 14, "health": 30}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STORE = os.path.join(DATA_DIR, "antibodies.json")
EMBED_MODEL = "gemini-embedding-001"
# 0.78 calibrated on gemini-embedding-001: paraphrases of the same rumor score
# ~0.80, different rumors ~0.70, unrelated text floors at ~0.50 — so this catches
# genuine matches without cross-matching distinct claims.
THRESHOLD = float(os.getenv("VIVEKA_MATCH_THRESHOLD", "0.78"))
# difflib ratio is far more permissive than cosine, so the fuzzy fallback must be
# STRICTER, not looser — 0.62 cross-matched different rumors sharing boilerplate.
FUZZY_THRESHOLD = 0.80
MAX_LEARNED = 5000           # cap so the store can't grow unbounded
_NEG = ("not", "n't", "never", "no ", "false", "नहीं", " नही")

_store: list[dict] = []
_loaded = False
_lock = threading.Lock()     # antibodies.json is read-modify-written per check


def _embed(text: str) -> list[float] | None:
    if not config.GEMINI_API_KEY:
        return None
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent",
            params={"key": config.GEMINI_API_KEY},
            json={"model": f"models/{EMBED_MODEL}", "content": {"parts": [{"text": text[:2000]}]}},
            timeout=15,
        )
        if r.status_code != 200:
            return None
        return r.json().get("embedding", {}).get("values")
    except Exception:
        return None


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _save() -> None:
    """Atomic write under a lock — concurrent checks otherwise interleave writes
    and corrupt the file, which silently wipes every learned rumor on next load."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_store, f, ensure_ascii=False)
    os.replace(tmp, STORE)


def _load() -> None:
    global _store, _loaded
    if _loaded:
        return
    with _lock:                       # guard cold-start load+seed against concurrent first requests
        if _loaded:
            return
        if os.path.exists(STORE):
            try:
                with open(STORE, encoding="utf-8") as f:
                    _store = json.load(f)
            except Exception:
                _store = []
        if not _store:
            _seed()
        _loaded = True


def _seed() -> None:
    global _store
    from antibodies_seed import SEED
    out = []
    for i, item in enumerate(SEED):
        out.append({
            "id": f"seed{i}",
            "key_text": item["key_text"],
            "vec": _embed(item["key_text"]),
            "result": item["result"],
            "checks": item.get("checks", 1),
            "age": item.get("age", "earlier"),
        })
    _store = out
    _save()


def _claim_negation_flip(a: str, b: str) -> bool:
    """Conservative polarity check: only fires when ONE text contains an explicit
    claim-negating phrase ('does not', 'doesn't', 'is not', 'no evidence') and the
    other doesn't. Deliberately narrow — generic 'no'/'not' (e.g. 'no need for the
    hospital') must NOT trigger it, or it rejects legitimate matches."""
    phrases = (" does not ", " do not ", "doesn't", "don't", " is not ", " are not ",
               "isn't", "no evidence", "not true", "is false", "नहीं ")
    na = any(p in (" " + a.lower() + " ") for p in phrases)
    nb = any(p in (" " + b.lower() + " ") for p in phrases)
    return na != nb


def _expired(e: dict) -> bool:
    """True if a LEARNED entry is past its domain TTL — so we re-check instead of
    serving a possibly-stale verdict. Seeds (curated timeless myths) never expire."""
    if str(e.get("id", "")).startswith("seed"):
        return False
    ts = e.get("ts")
    if not ts:
        return False                      # legacy entry without a timestamp
    domain = (e.get("result") or {}).get("domain", "general")
    return (time.time() - ts) > TTL_DAYS.get(domain, 7) * 86400


def match(text: str) -> dict | None:
    """Return {entry, score} for the closest known rumor above threshold, else None.
    A matched-but-expired learned entry returns None so the claim is re-verified."""
    _load()
    if not _store:
        return None
    qv = _embed(text)
    best, best_s = None, 0.0
    if qv:
        for e in _store:
            if not e.get("vec"):
                continue
            s = _cos(qv, e["vec"])
            if s > best_s:
                best_s, best = s, e
        if best and best_s >= THRESHOLD and not _claim_negation_flip(text, best.get("key_text", "")):
            return None if _expired(best) else {"entry": best, "score": round(best_s, 3)}
        return None
    # No embeddings (offline) -> fuzzy text match so seeds still hit.
    for e in _store:
        s = difflib.SequenceMatcher(None, text.lower(), e["key_text"].lower()).ratio()
        if s > best_s:
            best_s, best = s, e
    if best and best_s >= FUZZY_THRESHOLD and not _claim_negation_flip(text, best.get("key_text", "")):
        return None if _expired(best) else {"entry": best, "score": round(best_s, 3)}
    return None


def pulse_view(limit: int = 12) -> list[dict]:
    """The real rumors Viveka knows (seeded + learned), for the Pulse surface."""
    _load()
    with _lock:                       # snapshot — remember() may be mutating _store concurrently
        snapshot = list(_store)
    out = []
    for e in snapshot:
        r = e.get("result", {})
        claim = (r.get("claims") or [e.get("key_text", "")])[0]
        out.append({
            "id": e.get("id"),
            "claim": claim[:140],
            "gloss": (r.get("meaningEn", "") or "")[:140],
            "verdict": r.get("verdict", "human"),
            "checks": int(e.get("checks", 1)),
            "domain": r.get("domain", "general"),
            "age": e.get("age", "earlier"),
        })
    out.sort(key=lambda x: x["checks"], reverse=True)
    return out[:limit]


def remember(text: str, result: dict) -> None:
    """Store a freshly-checked novel claim so the next identical forward is instant.

    Privacy control: set VIVEKA_NO_LEARN=1 to disable server-side learning entirely
    (curated seeds still load; no user-submitted text is ever persisted). Documented
    in the System Card so the data-handling claim matches the code."""
    if os.getenv("VIVEKA_NO_LEARN"):
        return
    _load()
    if result.get("verdict") in ("opinion", "human"):
        return  # opinions and unresolved abstentions aren't worth remembering
    # Never auto-cache high-stakes (health/communal/disaster) verdicts: a single
    # poisoned verdict shouldn't be served instantly to everyone, and these claims
    # are time-sensitive — always re-verify them live.
    cart = config.CARTRIDGES.get(result.get("domain", "general"), config.CARTRIDGES[config.DEFAULT_CARTRIDGE])
    if cart.escalation == "fast":
        return
    # Anti-poisoning: only learn a verdict that is BOTH confident AND corroborated by
    # an authoritative source (gov / WHO / a real fact-checker). The live engine is
    # modest end-to-end (0.398), so a shaky, uncorroborated verdict must never be
    # cached and then re-served to the next person as an instant, confident record.
    try:
        conf = int(result.get("confidence", 0))
    except Exception:
        conf = 0
    corroborated = any((s.get("tier") == "authoritative") or s.get("is_factcheck")
                       for s in (result.get("sources") or []))
    if conf < 60 or not corroborated:
        return
    entry = {
        "id": f"ab{len(_store)}",
        "key_text": text[:300],
        "vec": _embed(text),
        "result": {k: v for k, v in result.items() if k not in ("matched", "matchChecks", "matchAge")},
        "checks": 1,
        "age": "just now",
        "ts": time.time(),          # for the TTL staleness check in _expired()
    }
    with _lock:
        _store.append(entry)
        if len(_store) > MAX_LEARNED:            # keep seeds + newest, drop oldest learned
            seeds = [e for e in _store if str(e.get("id", "")).startswith("seed")]
            learned = [e for e in _store if not str(e.get("id", "")).startswith("seed")]
            _store[:] = seeds + learned[-(MAX_LEARNED - len(seeds)):]
        _save()
