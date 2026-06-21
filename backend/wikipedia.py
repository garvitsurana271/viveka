"""Wikipedia REST API — keyless, free. Background evidence for novel claims."""
from __future__ import annotations
import httpx

# Wikimedia's robot policy 403s a User-Agent without a URL. This compliant UA passes.
HEADERS = {"User-Agent": "Viveka/0.1 (https://409.ai; dev@409.ai)"}


async def search(query: str, lang: str = "en", max_results: int = 2) -> list[dict]:
    out: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=8, headers=HEADERS) as c:
            r = await c.get(
                f"https://{lang}.wikipedia.org/w/rest.php/v1/search/page",
                params={"q": query, "limit": max_results},
            )
            if r.status_code != 200:
                return []
            for p in r.json().get("pages", []):
                title = p.get("title", "")
                slug = title.replace(" ", "_")
                extract = p.get("description") or ""
                url = f"https://{lang}.wikipedia.org/wiki/{slug}"
                try:
                    sr = await c.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{slug}")
                    if sr.status_code == 200:
                        j = sr.json()
                        extract = j.get("extract") or extract
                        url = (j.get("content_urls", {}).get("desktop", {}).get("page")) or url
                except Exception:
                    pass
                out.append({"org": "Wikipedia", "badge": "W", "url": url, "note": extract[:240]})
    except Exception:
        return out
    return out
