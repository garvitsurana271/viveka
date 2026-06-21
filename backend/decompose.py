"""Stage 1 — read the message: detect language, domain, and atomic claims."""
from __future__ import annotations
from llm import complete_json

SYSTEM = (
    "You are a careful, neutral fact-checking analyst. You break a forwarded chat "
    "message into the specific factual claims it makes, so each can be checked. "
    "You never add claims that aren't there. You output only JSON."
)


def decompose(text: str) -> dict:
    prompt = f'''A forwarded chat message (may be in any language, may include emojis):
"""{text}"""

Return ONLY this JSON:
{{
  "language": "<the message's language, English name e.g. Hindi, English, Tamil>",
  "domain": "health | disaster | product | communal | finance | general",
  "is_claim": true or false,
  "query": "<a SHORT 2-5 word web/encyclopedia search query of the key entities, in English>",
  "claims": ["<atomic, checkable factual claim>", "..."]
}}

Rules:
- "query": the entity/topic to look up (e.g. "Great Wall visible from space", "garlic COVID cure"), NOT the whole message.
- "claims": 1 to 4 atomic factual claims that could be true or false. Strip greetings, emojis, "forward this", opinions.
- "is_claim": false if the message is only a joke, opinion, greeting, or satire with nothing factual to verify (then "claims" may be empty).
- "domain": communal = rumors of kidnapping/violence/mobs; disaster = floods/quakes/emergencies; finance = money/scams/banks; health = medical/cures; product = product safety/recalls; else general.
'''
    # Gemma 4 "thinks" before answering, and thinking counts against the output
    # budget — give it generous room so the JSON answer isn't truncated to empty.
    return complete_json(SYSTEM, prompt, max_tokens=8192)
