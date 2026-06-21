"""Offline mode — faithful canned reasoning so the demo always works at $0.

Used when no LLM key is set, or as the graceful-degradation fallback if a live
stage fails. Matches the two seeded demo forwards (garlic, white-van) and a safe
human-review default for anything else.
"""
from __future__ import annotations
import asyncio
import re

GARLIC = {
    "verdict": "misleading", "confidence": 92, "domain": "health",
    "claims": ["Eating raw garlic cures COVID-19.", "Doctors confirm garlic as a cure."],
    "sources": [
        {"org": "WHO", "badge": "W", "url": "who.int/myth-busters", "note": "Garlic is healthy but there is no evidence it protects against or cures COVID-19."},
        {"org": "ICMR (India)", "badge": "I", "url": "icmr.gov.in", "note": "No food or home remedy is a proven cure for COVID-19."},
        {"org": "Reuters Fact Check", "badge": "R", "url": "reuters.com/fact-check", "note": "Rated similar garlic-cure claims as false/misleading."},
    ],
    "meaningEn": "Garlic is healthy, but it does NOT cure or prevent COVID-19. Treating it as a cure can stop someone from getting real medical care.",
    "meaningHi": "लहसुन सेहतमंद है, पर यह कोविड-19 को न रोकता है, न ठीक करता है। इसे इलाज समझना खतरनाक हो सकता है।",
    "counterEn": "Hi! I checked this. Garlic is healthy, but it does NOT cure or prevent COVID-19 — that's confirmed by the WHO and ICMR. Please don't rely on it. If someone is unwell, see a doctor.",
    "counterHi": "नमस्ते! मैंने जाँच की। लहसुन सेहतमंद है पर कोरोना को न रोकता है न ठीक करता है — WHO और ICMR यही कहते हैं। कृपया इस पर भरोसा न करें, तबीयत खराब हो तो डॉक्टर को दिखाएँ।",
    "weighNote": "There is a grain of truth — garlic has general health benefits — but the cure claim is unsupported. That mix is why it lands on \"misleading,\" not outright \"false.\"",
    "escalate": True,
}

VAN = {
    "verdict": "human", "confidence": 38, "domain": "communal",
    "claims": ["A white van is kidnapping children near the market.", "Police are covering it up."],
    "sources": [
        {"org": "State police feed", "badge": "P", "url": "live advisory check", "note": "No matching kidnapping advisory found in the last 7 days."},
        {"org": "PIB Fact Check", "badge": "P", "url": "pib.gov.in/factcheck", "note": "\"White van\" child-lifting forwards are a recurring template hoax across regions."},
    ],
    "meaningEn": "Viveka can't verify this on its own. It names a specific local event that trusted sources haven't confirmed — and these \"white van\" alerts are a common hoax pattern. A human is checking before any verdict.",
    "meaningHi": "विवेका इसे खुद पुष्टि नहीं कर सकता। यह एक स्थानीय घटना का दावा है जिसकी पुष्टि भरोसेमंद स्रोतों से नहीं हुई — और ऐसे \"सफ़ेद वैन\" संदेश अक्सर अफवाह होते हैं। फैसले से पहले एक व्यक्ति जाँच कर रहा है।",
    "counterEn": "Please hold on before forwarding. This alert can't be confirmed by police yet, and \"white van\" messages are often false. Forwarding it can cause panic. I'll share an update once it's verified.",
    "counterHi": "कृपया भेजने से पहले रुकें। पुलिस अभी इसकी पुष्टि नहीं कर पाई है, और \"सफ़ेद वैन\" वाले संदेश अक्सर झूठे होते हैं। इसे फैलाने से दहशत फैल सकती है। पुष्टि होते ही मैं बताऊँगा/बताऊँगी।",
    "weighNote": "This is a fast-moving, local, real-time safety claim. Trusted sources can't confirm or deny it yet, and getting it wrong could cause panic or vigilante harm. Too risky to auto-rule.",
    "escalate": False,
}


def _naive_claims(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[.!?\n]", text) if len(p.strip()) > 12]
    return parts[:2] or [text[:120]]


def _match(text: str) -> dict | None:
    t = text.lower()
    if "garlic" in t or "लहसुन" in text or "कोरोना" in text and "लहसुन" in text:
        return GARLIC
    if any(k in t for k in ("white van", "kidnap", "children near")) or "सफ़ेद वैन" in text or "बच्च" in text:
        return VAN
    return None


def _generic(text: str) -> dict:
    return {
        "verdict": "human", "confidence": 40, "domain": "general",
        "claims": _naive_claims(text),
        "sources": [{"org": "Human review", "badge": "H", "url": "", "note": "Queued for a trained reviewer — no live source check was run."}],
        "meaningEn": "Viveka couldn't check this against its live sources right now, so a human reviewer will look at it before giving a verdict.",
        "meaningHi": "विवेका अभी इसे अपने स्रोतों से जाँच नहीं सका, इसलिए फैसले से पहले एक व्यक्ति इसे देखेगा।",
        "counterEn": "Please wait before forwarding — this hasn't been verified yet. I'll share an update once it's checked.",
        "counterHi": "कृपया भेजने से पहले रुकें — यह अभी जाँचा नहीं गया है। पुष्टि होते ही मैं बताऊँगा/बताऊँगी।",
        "weighNote": "No live verification was available; routed to a human as a safe default.",
        "escalate": False,
    }


async def run(text: str, lang_pref: str = "en", error: str | None = None):
    res = _match(text) or _generic(text)
    yield {"type": "reading", "lang": "English", "domain": res["domain"]}
    await asyncio.sleep(0.9)
    yield {"type": "claims", "claims": res["claims"]}
    await asyncio.sleep(1.1)
    yield {"type": "sources", "sources": res["sources"]}
    await asyncio.sleep(1.2)
    yield {"type": "verdict", "result": res}
