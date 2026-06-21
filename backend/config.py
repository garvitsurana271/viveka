"""Viveka configuration: provider selection and domain cartridges.

Plain config so adding a claim domain or swapping the LLM never touches engine
code. With no GEMINI_API_KEY set, the engine runs in OFFLINE mode (canned but
faithful reasoning for the demo samples) — zero key, zero cost, never fails.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# --- LLM provider (ports-and-adapters; see llm.py) ---------------------------
# "gemini" (free tier, default) | "claude" (paid drop-in) | "groq" (free text)
LLM_PROVIDER = os.getenv("VIVEKA_LLM_PROVIDER", "gemini").lower()

# Gemini accepts either GEMINI_API_KEY or GOOGLE_API_KEY (the SDK's default env).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
# Default to Gemma 4 (open model on the Gemini API) — effectively unlimited RPD on
# the free tier. Note: Gemma ignores system_instruction and JSON mode; llm.py
# adapts automatically for any model id starting with "gemma".
GEMINI_MODEL = os.getenv("VIVEKA_GEMINI_MODEL", "gemma-4-31b-it")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("VIVEKA_CLAUDE_MODEL", "claude-opus-4-8")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Optional free Google Fact Check Tools API key. Without it, retrieval falls
# back to keyless Wikipedia — the engine still runs.
GOOGLE_FACTCHECK_API_KEY = os.getenv("GOOGLE_FACTCHECK_API_KEY", "")

# --- WhatsApp Cloud API (the last-mile: forward a message, get a verdict) -----
# User-initiated service conversations are free & unlimited on Meta's Cloud API,
# which fits exactly: people FORWARD a suspicious message and we reply. All keys
# optional — without them the webhook simply reports "not configured".
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")          # Graph API access token
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")    # phone-number id to send from
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "viveka-verify")  # webhook handshake

def whatsapp_ready() -> bool:
    return bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID)


def llm_available() -> bool:
    """True when the selected provider has a usable key."""
    if LLM_PROVIDER == "gemini":
        return bool(GEMINI_API_KEY)
    if LLM_PROVIDER == "claude":
        return bool(ANTHROPIC_API_KEY)
    if LLM_PROVIDER == "groq":
        return bool(GROQ_API_KEY)
    return False


# Force offline (canned) mode regardless of keys — useful for a guaranteed demo.
FORCE_OFFLINE = os.getenv("VIVEKA_OFFLINE", "").lower() in ("1", "true", "yes")

def offline() -> bool:
    return FORCE_OFFLINE or not llm_available()


# --- Domain cartridges -------------------------------------------------------
@dataclass
class Cartridge:
    """A claim domain = its trusted sources + how fast it escalates to a human.

    `escalation` drives abstention: 'fast' domains route to a human on any
    uncertainty because a wrong answer is severe (health, disaster, communal).
    """
    key: str
    label: str
    trusted_sources: list[str] = field(default_factory=list)
    escalation: str = "normal"  # "fast" | "normal" | "conservative"


CARTRIDGES: dict[str, Cartridge] = {
    "health": Cartridge("health", "Health & safety",
        ["who.int", "icmr.gov.in", "fssai.gov.in", "mohfw.gov.in"], escalation="fast"),
    "disaster": Cartridge("disaster", "Disaster & emergency",
        ["ndma.gov.in", "imd.gov.in", "pib.gov.in"], escalation="fast"),
    "product": Cartridge("product", "Product safety & recalls",
        ["fssai.gov.in", "consumeraffairs.nic.in"], escalation="normal"),
    "communal": Cartridge("communal", "Communal / violence rumor",
        ["pib.gov.in"], escalation="fast"),  # the lynching category — never auto-verify
    "finance": Cartridge("finance", "Money & scams",
        ["rbi.org.in", "pib.gov.in"], escalation="normal"),
    "general": Cartridge("general", "General / political",
        ["pib.gov.in", "en.wikipedia.org"], escalation="conservative"),
}

DEFAULT_CARTRIDGE = "general"

# Abstain (route to human) when confidence is below the cartridge threshold.
ABSTAIN_BELOW = {"fast": 70, "normal": 55, "conservative": 45}
