"""Disk-backed cache for Gemma calls during evaluation.

Gemma's quota is 1,500 requests/day. A single AVeriTeC dev run (500 claims, a
few calls each) can eat the whole budget — so re-running after a code change
would be impossible without caching. Every successful call is memoised to disk
keyed by a hash of (model, max_tokens, system, prompt). Identical prompts on a
re-run return instantly and cost nothing; only changed or previously-failed
prompts hit the API.

Failures (empty Gemma response → LLMError) are NEVER cached, so a re-run retries
them instead of locking in a bad result.
"""
from __future__ import annotations
import os
import sys
import json
import hashlib

# Make the backend package importable whether run as `python eval/x.py` or `-m`.
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import config          # noqa: E402
import llm             # noqa: E402

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# Per-process counters so a run can report cache hit-rate and real API spend.
# (Rate-limit throttling lives in llm._gemini, gated by VIVEKA_RPM_THROTTLE, so
# it covers both this cached path and the live analyze/verify calls.)
STATS = {"hits": 0, "misses": 0, "errors": 0}


def _key(system: str, prompt: str, max_tokens: int, model: str) -> str:
    h = hashlib.sha256()
    h.update("\x00".join([model, str(max_tokens), system or "", prompt or ""]).encode("utf-8"))
    return h.hexdigest()


def cached_complete_json(system: str, prompt: str, max_tokens: int = 8192):
    """llm.complete_json with a transparent disk cache. Raises on a failed call
    (caller decides how to degrade), and does not cache the failure."""
    key = _key(system, prompt, max_tokens, config.GEMINI_MODEL)
    path = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            STATS["hits"] += 1
            return json.load(f)["response"]
    try:
        resp = llm.complete_json(system, prompt, max_tokens=max_tokens)
    except Exception:
        STATS["errors"] += 1
        raise
    STATS["misses"] += 1
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"response": resp}, f, ensure_ascii=False)
    return resp


def reset_stats() -> None:
    STATS.update(hits=0, misses=0, errors=0)
