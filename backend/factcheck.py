"""Google Fact Check Tools API — keyed but free (quota-limited).

Returns already-published fact-checks (ClaimReview) matching a query. Without a
key this returns [] and the engine falls back to Wikipedia — it still runs.
"""
from __future__ import annotations
import httpx
import config

ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


async def search(query: str, lang: str = "en", max_results: int = 4) -> list[dict]:
    if not config.GOOGLE_FACTCHECK_API_KEY:
        return []
    params = {
        "query": query,
        "key": config.GOOGLE_FACTCHECK_API_KEY,
        "pageSize": max_results,
        "languageCode": lang,
    }
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(ENDPOINT, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
    except Exception:
        return []

    out: list[dict] = []
    for claim in data.get("claims", []):
        for rev in claim.get("claimReview", []):
            pub = (rev.get("publisher") or {}).get("name") or (rev.get("publisher") or {}).get("site") or "Fact check"
            rating = rev.get("textualRating")
            note = (rev.get("title") or claim.get("text") or "").strip()
            if rating:
                note = (note + f" — rated: {rating}").strip(" —")
            out.append({
                "org": pub,
                "badge": pub[:1].upper(),
                "url": rev.get("url", ""),
                "note": note[:240],
                "is_factcheck": True,   # a published ClaimReview — top-tier evidence
            })
            if len(out) >= max_results:
                return out
    return out
