"""Stage 3 — weigh the evidence and produce a calibrated, grounded verdict."""
from __future__ import annotations
from llm import complete_json

SYSTEM = (
    "You verify forwarded chat messages for ordinary people, many of them elderly "
    "or low-literacy. You ground every judgement ONLY in the evidence provided to "
    "you — you never invent sources or facts. You are calibrated: when the evidence "
    "is thin, or a claim is local/real-time and high-stakes (kidnapping, violence, "
    "disaster), you abstain and route to a human rather than guess. You output only JSON."
)


def reason(text: str, claims: list[str], evidence: list[dict], domain: str) -> dict:
    ev_lines = "\n".join(f"- {e['org']}: {e['note']} ({e['url']})" for e in evidence) or "(no external evidence was retrieved)"
    claim_lines = "\n".join(f"- {c}" for c in claims)
    prompt = f'''Original message:
"""{text}"""

Claims to judge:
{claim_lines}

Evidence found:
{ev_lines}

Domain: {domain}

Decide a verdict, grounded ONLY in the evidence above. Return ONLY this JSON:
{{
  "verdict": "true | misleading | false | human | opinion",
  "confidence": <integer 0-100>,
  "meaning_en": "<at most 2 short, simple sentences: what this means for the reader>",
  "meaning_hi": "<Hindi (Devanagari) translation of meaning_en>",
  "counter_en": "<a short, polite reply the reader can forward back to the group to correct it; name the source; warm tone>",
  "counter_hi": "<Hindi (Devanagari) translation of counter_en>",
  "weigh_note": "<1-2 sentences: how you weighed the evidence, and why this verdict rather than a neighbouring one>"
}}

Rules:
- Use "misleading" when there is a grain of truth but the strong claim is unsupported.
- Use "human" (low confidence) when evidence can neither confirm nor deny, especially for local/real-time safety claims — do NOT guess.
- Use "opinion" only if there is nothing factual to verify.
- Keep meaning_en and counter_en simple enough for a low-literacy reader. No jargon.
'''
    # Generous ceiling so Gemma's (non-deterministic) thinking never starves the
    # bilingual JSON answer. gemma-4-31b-it allows up to 32768 output tokens.
    return complete_json(SYSTEM, prompt, max_tokens=30000)
