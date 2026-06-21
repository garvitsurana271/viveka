"""Image forwards → text, then the normal verification pipeline runs.

Gemma 4 is natively multimodal with multilingual OCR — a WhatsApp screenshot
(even in Hindi) goes straight to it, no separate OCR engine. Voice is handled
entirely in the browser (Web Speech API) and arrives as text, so there is no
audio path here — nothing touches a rate-limited model.
"""
from __future__ import annotations
import base64
import config


def _client():
    from google import genai
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(api_key=config.GEMINI_API_KEY)


def image_to_text(image_b64: str, mime: str = "image/png") -> str:
    from google.genai import types
    client = _client()
    part = types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type=mime)
    instruction = (
        "This is a forwarded image or screenshot that someone received. "
        "Extract the exact text of the message/claim shown, in its original "
        "language. If there is little or no text, briefly state the claim the "
        "image makes. Output ONLY that text — no description, no preamble."
    )
    # Gemma's vision call occasionally returns empty (its thinking eats the output
    # budget). OCR is a single extraction step — an empty result means no text at
    # all — so we retry until we get one, with the max output ceiling.
    for _ in range(4):
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,  # Gemma 4 — multimodal OCR
            contents=[instruction, part],
            config={"max_output_tokens": 32768, "temperature": 0.1},
        )
        text = (resp.text or "").strip()
        if text:
            return text
    return ""
