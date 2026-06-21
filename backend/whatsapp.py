"""WhatsApp Cloud API last-mile — forward a suspicious message, get a verdict.

This is the reach no fact-checking tipline has at $0: people already forward
rumors on WhatsApp, so the bot meets them there. User-initiated service
conversations are free and unlimited on Meta's Cloud API, and replying within
the 24-hour window costs nothing — which is exactly this flow (they message us
first). Meta's Jan-2026 ban on *general-purpose* AI chatbots doesn't apply: this
is a single-purpose misinformation-verification service.

Two webhook entry points (wired in app.py):
  GET  /webhook  — Meta's verification handshake.
  POST /webhook  — an inbound message -> run the engine -> reply.

Without WHATSAPP_TOKEN / WHATSAPP_PHONE_ID set, send is a no-op and the webhook
still 200s, so the rest of the app is unaffected.
"""
from __future__ import annotations
import httpx
import config
import engine

GRAPH = "https://graph.facebook.com/v21.0"

# Verdict -> a plain, forward-friendly header for the reply.
_HEAD = {
    "true": "✅ Likely TRUE",
    "false": "❌ FALSE",
    "misleading": "⚠️ MISLEADING",
    "human": "🔎 NEEDS A HUMAN CHECK",
    "opinion": "💬 NOT A FACTUAL CLAIM",
}


def verify_challenge(mode: str, token: str, challenge: str) -> str | None:
    """Meta calls GET /webhook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
    We echo the challenge only if the token matches."""
    if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return challenge
    return None


def _format_reply(result: dict, lang: str = "en") -> str:
    """Turn an engine verdict into a short WhatsApp message: verdict + why +
    the ready-to-forward counter-message + a source."""
    verdict = result.get("verdict", "human")
    head = _HEAD.get(verdict, _HEAD["human"])
    conf = result.get("confidence")
    if verdict not in ("opinion",) and conf is not None:
        head += f"  ({conf}% confident)"

    hi = lang.startswith("hi")
    why = (result.get("meaningHi") if hi else result.get("meaningEn")) or ""
    counter = (result.get("counterHi") if hi else result.get("counterEn")) or ""

    lines = [head]
    if why:
        lines += ["", why]
    srcs = [s.get("org", "") for s in (result.get("sources") or []) if s.get("org")][:3]
    if srcs:
        lines += ["", "Sources: " + ", ".join(srcs)]
    if counter:
        lines += ["", "↪️ You can forward this back:", f"“{counter}”"]
    lines += ["", "— Viveka · this was checked automatically, not a human verdict."]
    return "\n".join(lines)


async def send_text(to: str, body: str) -> bool:
    if not config.whatsapp_ready():
        return False
    url = f"{GRAPH}/{config.WHATSAPP_PHONE_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text",
               "text": {"body": body[:4000]}}  # WhatsApp text cap
    headers = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(url, json=payload, headers=headers)
            return r.status_code < 300
    except Exception:
        return False


def _extract_message(body: dict) -> dict | None:
    """Pull the first inbound message out of Meta's webhook envelope.
    Returns {from, text, lang} or None (status callbacks, etc.)."""
    try:
        change = body["entry"][0]["changes"][0]["value"]
        msg = (change.get("messages") or [None])[0]
        if not msg:
            return None
        frm = msg.get("from")
        if msg.get("type") == "text":
            return {"from": frm, "text": msg["text"]["body"], "lang": "en"}
        # Non-text (image/audio) — acknowledge with guidance for now; the web app
        # handles those modalities, and image support can be added by downloading
        # the media id via the Graph API.
        return {"from": frm, "text": "", "lang": "en"}
    except Exception:
        return None


async def handle_inbound(body: dict) -> None:
    """Process one webhook POST: run the engine on the forwarded text and reply.
    Best-effort — never raises into the webhook (Meta retries on non-200)."""
    msg = _extract_message(body)
    if not msg or not msg.get("from"):
        return
    text = (msg.get("text") or "").strip()
    if not text:
        await send_text(msg["from"],
                        "Forward me the *text* of a suspicious message and I'll check it "
                        "against trusted sources. (Image and voice checks are on the web app.)")
        return
    try:
        result = await engine.run_check_final(text, lang_pref=msg.get("lang", "en"))
        reply = _format_reply(result, msg.get("lang", "en")) if result else \
            "I couldn't check that just now — please try again in a moment."
    except Exception:
        reply = "I couldn't check that just now — please try again in a moment."
    await send_text(msg["from"], reply)
