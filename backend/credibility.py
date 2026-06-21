"""Source credibility tiers — rank evidence so authoritative sources surface
first (and can be badged in the UI). Like professional tools, Viveka should lean
on health/government authorities and established fact-checkers over random blogs.
"""
from __future__ import annotations
import re

# Substring match on the source domain.
AUTHORITATIVE = (
    ".gov", "gov.in", "gov.uk", "gov.au", "gov.za", "gov.sg", "canada.ca",
    "europa.eu", "un.org", "nhs.uk", "who.int", "cdc.gov", "nih.gov",
    "nlm.nih.gov", "ncbi.nlm", "icmr", "mohfw", "pib.gov", "rbi.org", "fssai",
    "ndma.gov", "imd.gov",
    "nature.com", "sciencedirect", "thelancet", "nejm.org", "mayoclinic.org",
    "snopes.com", "reuters.com", "apnews.com", "factcheck.org", "politifact",
    "fullfact.org", "altnews.in", "boomlive", "factly.in", "aap.com.au",
    "afp.com", "vishvasnews", "newschecker", "pesacheck",
)
REPUTABLE = (
    "wikipedia.org", "britannica.com", "bbc.", "nytimes.com", "theguardian",
    "washingtonpost", "healthline.com", "webmd.com", "medicalnewstoday",
    "ndtv.com", "thehindu.com", "indianexpress", "hindustantimes", "timesofindia",
    "livemint", "scroll.in", "thequint", "npr.org", "cnn.com", "forbes.com",
    "nationalgeographic", "smithsonianmag", "scientificamerican",
)


def tier(domain: str) -> tuple[str, int]:
    d = (domain or "").lower()
    if any(k in d for k in AUTHORITATIVE):
        return "authoritative", 3
    if any(k in d for k in REPUTABLE):
        return "reputable", 2
    return "web", 1


def _host(url: str, fallback: str = "") -> str:
    d = re.sub(r"^https?://(www\.)?", "", url or "")
    return (d.split("/")[0] or fallback) if d else fallback


def tier_source(s: dict) -> tuple[str, int]:
    """Tier a retrieved source. Sources name their org inconsistently (e.g.
    'Wikipedia' rather than 'wikipedia.org'), so tier on the URL host and fall
    back to the org name."""
    return tier(_host(s.get("url", ""), s.get("org", "")))
