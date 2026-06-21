"""Free, keyless web search via ddgs (aggregates DuckDuckGo / Bing / Google).

This is the retrieval depth that Wikipedia alone lacked — real web pages, including
published fact-checks — at $0. Returns the same source shape the engine uses.
"""
from __future__ import annotations
import asyncio
import re


def _domain(url: str) -> str:
    d = re.sub(r"^https?://(www\.)?", "", url or "")
    return (d.split("/")[0] or "web")[:40]


def _search_sync(query: str, max_results: int = 3) -> list[dict]:
    try:
        from ddgs import DDGS
        out = []
        for x in DDGS(timeout=8).text(query, max_results=max_results):
            url = x.get("href", "") or ""
            dom = _domain(url)
            note = (x.get("body", "") or "").strip()
            if not note:
                continue
            out.append({"org": dom, "badge": (dom[:1] or "?").upper(), "url": url, "note": note[:240]})
        return out
    except Exception:
        return []


async def search(query: str, max_results: int = 3) -> list[dict]:
    # Hard timeout so a slow/rate-limited ddgs can never stall a check —
    # retrieval just degrades to Wikipedia + Fact Check.
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search_sync, query, max_results), timeout=9
        )
    except Exception:
        return []
