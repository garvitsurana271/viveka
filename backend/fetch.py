"""P1 — full-document retrieval.

The AVeriTeC score is *gated* on evidence quality: a correct verdict on a bad
snippet scores zero. We were only ever reading ~240-char search previews. This
module fetches the actual article behind each result, extracts the clean main
text (trafilatura), and keeps the ~5-sentence window most relevant to the claim
— the single change the research flagged as the biggest lever (Papelo: 0.495 vs
0.465 on *live* web search). All $0: HTTP + CPU, no model calls.
"""
from __future__ import annotations
import re
import socket
import ipaddress
import asyncio
from urllib.parse import urlparse
import httpx
import trafilatura


def _is_public_host(host: str) -> bool:
    """Reject hosts that resolve to private/loopback/link-local/reserved IPs — an
    SSRF guard, since these URLs come from attacker-influenceable search results and
    a redirect could point the server at cloud metadata (169.254.169.254) or internal
    services."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
            return False
    return True

HEADERS = {"User-Agent": "Viveka/0.1 (https://409.ai; dev@409.ai) misinformation-checker"}
_SENT = re.compile(r"(?<=[.!?])\s+")
WINDOW_CHARS = 1500          # cap on the extracted window (lede + best passage) fed to the model
MAX_FETCH = 4                # how many of the top sources to fetch in full


async def fetch_text(url: str, timeout: float = 7.5) -> str:
    """Download a URL and return its clean main text ('' on any failure)."""
    if not url:
        return ""
    host = urlparse(url).hostname
    if not await asyncio.to_thread(_is_public_host, host):   # SSRF guard
        return ""
    try:
        # follow_redirects=False so a page can't 302 the server to an internal
        # address after the host check; most article URLs are already canonical.
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=HEADERS) as c:
            r = await c.get(url)
        if r.status_code != 200 or not r.text:
            return ""
    except Exception:
        return ""
    try:
        text = await asyncio.to_thread(
            trafilatura.extract, r.text,
            include_comments=False, include_tables=False, favor_precision=True,
        )
        return text or ""
    except Exception:
        return ""


def best_window(text: str, query: str, n: int = 6) -> str:
    """The n-sentence window most relevant to the claim, prefixed with the
    article lede. A $0 passage reranker: it finds the part of the article that
    addresses the claim, and the lede because fact-checks state their verdict up
    front. Rarer query terms are weighted higher (cheap IDF)."""
    text = (text or "").strip()
    if not text:
        return ""
    sents = [s for s in _SENT.split(text) if len(s.strip()) > 1]
    if len(sents) <= n:
        return text[:WINDOW_CHARS]
    terms = [t for t in re.findall(r"\w+", (query or "").lower()) if len(t) > 2]
    if not terms:
        return " ".join(sents[:n])[:WINDOW_CHARS]

    # cheap IDF: a term appearing in fewer sentences is more discriminating
    lowered = [s.lower() for s in sents]
    df = {t: sum(1 for s in lowered if t in s) or 1 for t in set(terms)}
    weight = {t: 1.0 / df[t] for t in df}

    def score(i: int) -> float:
        window = " ".join(lowered[i:i + n])
        return sum(weight[t] for t in set(terms) if t in window)

    best_i = max(range(len(sents) - n + 1), key=score)
    lede = " ".join(sents[:2]).strip()
    if best_i <= 2:                              # best window already includes the opening
        return " ".join(sents[: n + 2])[:WINDOW_CHARS]
    window = " ".join(sents[best_i:best_i + n]).strip()
    return f"{lede} […] {window}"[:WINDOW_CHARS]


async def enrich(sources: list[dict], query: str, max_fetch: int = MAX_FETCH, n: int = 5) -> list[dict]:
    """Replace the top sources' short snippets with a relevant full-article window.
    Leaves the snippet in place when a fetch fails, so this only ever adds signal."""
    targets = [s for s in sources[:max_fetch] if s.get("url") and not s.get("full_doc")]
    if not targets:
        return sources
    texts = await asyncio.gather(*[fetch_text(s["url"]) for s in targets], return_exceptions=True)
    for s, txt in zip(targets, texts):
        if isinstance(txt, str) and len(txt) > len(s.get("note", "")):
            window = best_window(txt, query or s.get("note", ""), n)
            if window and len(window) > len(s.get("note", "")):
                s["note"] = window
                s["full_doc"] = True
    return sources
