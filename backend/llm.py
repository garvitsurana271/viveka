"""LLM provider abstraction (ports-and-adapters).

The engine depends ONLY on `complete_text` / `complete_json`. Swapping Gemini
(free) for Claude (paid) or Groq is a one-line env change in config.LLM_PROVIDER.

JSON mode: we set the response mime-type to application/json and describe the
required shape in the prompt, then json.loads — robust across SDK versions,
no dependence on a particular response_schema format.
"""
from __future__ import annotations
import json
import os
import re
import time
import random
import threading
from typing import Any
import config

_gemini_client = None

# Optional client-side rate limiter for batch/eval runs. Gemma's free tier is
# 15 RPM; set VIVEKA_RPM_THROTTLE to a per-call minimum gap in seconds (e.g.
# 4.3 -> ~14/min) so a long evaluation never trips a 429. Default 0 = off, so
# the live product is never slowed.
#
# Reservation-based + thread-safe: each caller reserves the next start slot
# (spaced THROTTLE seconds apart) and sleeps until it, then proceeds. So with
# several worker threads the request *starts* stay rate-limited while their
# network latencies overlap — a concurrent eval is rate-bound, not
# latency-bound, which roughly halves wall-clock vs strict serialisation.
_THROTTLE = float(os.getenv("VIVEKA_RPM_THROTTLE", "0") or "0")
_slot_lock = threading.Lock()
_next_slot = [0.0]


def _throttle() -> None:
    if _THROTTLE <= 0:
        return
    with _slot_lock:
        start_at = max(time.monotonic(), _next_slot[0])
        _next_slot[0] = start_at + _THROTTLE
    wait = start_at - time.monotonic()
    if wait > 0:
        time.sleep(wait)


class LLMError(RuntimeError):
    pass


def complete_text(system: str, prompt: str, *, max_tokens: int = 1024) -> str:
    if config.LLM_PROVIDER == "gemini":
        return _gemini(system, prompt, max_tokens, json_mode=False)
    if config.LLM_PROVIDER == "claude":
        return _claude(system, prompt, max_tokens, json_mode=False)
    if config.LLM_PROVIDER == "groq":
        return _groq(system, prompt, max_tokens, json_mode=False)
    raise LLMError(f"Unknown provider {config.LLM_PROVIDER!r}")


def complete_json(system: str, prompt: str, *, max_tokens: int = 8192,
                  temperature: float | None = None) -> Any:
    """JSON completion. Gemma 4 'thinks' before answering and that thinking
    counts against the output budget — so callers pass a generous max_tokens
    (the model stops when done, so a high ceiling only prevents truncation;
    gemma-4-31b-it allows up to 32768 output tokens). `temperature` overrides the
    default (used for self-consistency sampling)."""
    if config.LLM_PROVIDER == "gemini":
        raw = _gemini(system, prompt, max_tokens, json_mode=True, temperature=temperature)
    elif config.LLM_PROVIDER == "claude":
        raw = _claude(system, prompt, max_tokens, json_mode=True)
    elif config.LLM_PROVIDER == "groq":
        raw = _groq(system, prompt, max_tokens, json_mode=True)
    else:
        raise LLMError(f"Unknown provider {config.LLM_PROVIDER!r}")
    return _parse_json(raw)


def _parse_json(raw: str) -> Any:
    raw = (raw or "").strip()
    # Tolerate ```json fences or leading prose.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"[\[{].*[\]}]", raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise LLMError(f"Model returned non-JSON: {raw[:200]}")


# --- Gemini (default, free tier) — unified google-genai SDK ------------------
def _client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai  # lazy import
        if not config.GEMINI_API_KEY:
            raise LLMError("GEMINI_API_KEY not set. Free key at aistudio.google.com.")
        _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _gemini_client


def _gemini(system: str, prompt: str, max_tokens: int, json_mode: bool,
            temperature: float | None = None) -> str:
    client = _client()
    model = config.GEMINI_MODEL
    is_gemma = model.lower().startswith("gemma")
    cfg: dict[str, Any] = {
        "temperature": temperature if temperature is not None else (0.1 if json_mode else 0.3),
        "max_output_tokens": max_tokens,
    }
    if is_gemma:
        # Gemma on the Gemini API: no system_instruction, no JSON mode.
        # Fold the system prompt in, and force JSON via instruction + robust parse.
        contents = f"{system}\n\n{prompt}" if system else prompt
        if json_mode:
            contents += "\n\nRespond with ONLY a single valid JSON value — no prose, no markdown fences."
    else:
        contents = prompt
        if system:
            cfg["system_instruction"] = system
        if json_mode:
            cfg["response_mime_type"] = "application/json"
    resp = _gemini_call(client, model, contents, cfg)
    return (resp.text or "").strip()


# Transient API faults (503 overload, 500, 429) are NOT the same as Gemma's
# empty-thinking responses — for these, retry-with-backoff is the correct
# response, not a bigger token budget. We retry ONLY genuine server/rate faults
# and let everything else (incl. empty results) propagate unchanged.
_RETRY_STATUS = (429, 500, 502, 503, 504)
# Short backoff with jitter: this is an INTERACTIVE request, not a batch job. The
# old (2,5,12) ladder added up to 19s of pure sleep per call, and with 2-6 Gemma
# calls per check that was the dominant latency term. Jitter stops parallel
# retries from re-colliding on the same congested slot.
_BACKOFFS = (0.5, 1.5, 3.0)


def _gemini_call(client, model, contents, cfg):
    from google.genai import errors as genai_errors
    last = None
    for attempt in range(len(_BACKOFFS) + 1):
        _throttle()
        try:
            return client.models.generate_content(model=model, contents=contents, config=cfg)
        except (genai_errors.ServerError, genai_errors.ClientError) as e:
            code = getattr(e, "code", None) or getattr(e, "status_code", None)
            if code not in _RETRY_STATUS or attempt == len(_BACKOFFS):
                raise
            last = e
            time.sleep(_BACKOFFS[attempt] + random.uniform(0, 0.5))
    raise last  # unreachable


# --- Claude (optional paid drop-in) -----------------------------------------
def _claude(system: str, prompt: str, max_tokens: int, json_mode: bool) -> str:
    import anthropic
    if not config.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY not set.")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    sys = system + ("\nRespond ONLY with a single valid JSON value." if json_mode else "")
    msg = client.messages.create(
        model=config.CLAUDE_MODEL, max_tokens=max_tokens, system=sys,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# --- Groq (optional free fast text sidecar) ---------------------------------
def _groq(system: str, prompt: str, max_tokens: int, json_mode: bool) -> str:
    from groq import Groq
    if not config.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY not set.")
    client = Groq(api_key=config.GROQ_API_KEY)
    kwargs: dict[str, Any] = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
        system = system + "\nRespond ONLY with valid JSON."
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile", max_tokens=max_tokens, temperature=0.1,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        **kwargs,
    )
    return (resp.choices[0].message.content or "").strip()
