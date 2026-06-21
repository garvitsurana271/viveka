"""The verification engine: decompose -> retrieve -> reason -> calibrate.

`run_check` is an async generator that yields trace events as each stage
completes, so the UI can show the work live:
  {"type":"reading", "lang", "domain"}
  {"type":"claims",  "claims":[...]}
  {"type":"sources", "sources":[{org,badge,url,note}]}
  {"type":"verdict", "result":{...}}
  {"type":"error",   "message"}

With no LLM key (config.offline()), it serves faithful canned reasoning so the
demo always works. Any stage failure degrades to the offline/human path.
"""
from __future__ import annotations
import asyncio
import re
from collections import Counter
import config
from config import CARTRIDGES, DEFAULT_CARTRIDGE, ABSTAIN_BELOW
import factcheck
import wikipedia
import websearch
import credibility
import offline

VALID = ("true", "misleading", "false", "human", "opinion")

# Debate panel labels (AVeriTeC-style) -> product verdicts, for escalation.
_DEBATE_TO_PRODUCT = {"supported": "true", "refuted": "false",
                      "conflicting": "misleading", "nei": "human"}


def _keywords(text: str) -> list[str]:
    """Cheap keyword query from raw text (no Gemma) — used to start retrieval
    immediately, overlapping it with the analyze call."""
    words = [w for w in re.findall(r"[A-Za-zऀ-ॿ]+", text) if len(w) > 3][:7]
    kw = " ".join(words)
    return [kw] if kw else [text[:70]]


async def _retrieve(queries: list[str], domain: str, cap: int = 5, full_doc: bool = True) -> list[dict]:
    """Multi-source, multi-query retrieval: web search + Wikipedia + Fact Check,
    ALL fired in parallel (InFact-style static retrieval). Sources are ranked by
    RELEVANCE to the query first (credibility as tiebreak), capped per-domain so
    one noisy site can't flood the top-8, with trusted cartridge sources boosted,
    and the top few read in FULL (not just snippets)."""
    seen_q, qs = set(), []
    for q in (queries or []):
        q = (q or "").strip()
        if q and q.lower() not in seen_q:
            seen_q.add(q.lower())
            qs.append(q)
        if len(qs) >= cap:
            break
    if not qs:                                   # nothing to search -> abstain cleanly
        return []

    cart = CARTRIDGES.get(domain, CARTRIDGES[DEFAULT_CARTRIDGE])
    trusted = tuple(cart.trusted_sources)
    tasks = []
    for q in qs:
        tasks.append(websearch.search(q, max_results=3))
        tasks.append(wikipedia.search(q, max_results=1))   # FIX: was passing 1 as lang
        tasks.append(factcheck.search(q, max_results=2))   # FIX: was passing 2 as lang
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=12)
    except asyncio.TimeoutError:
        results = []
    out: list[dict] = []
    for r in results:
        if isinstance(r, list):
            out.extend(r)

    qterms = {t for q in qs for t in re.findall(r"\w+", q.lower()) if len(t) > 2}

    def _rel(s: dict) -> float:
        blob = (s.get("note", "") + " " + s.get("org", "")).lower()
        return sum(1 for t in qterms if t in blob) / (len(qterms) or 1)

    seen, host_count, ded = set(), Counter(), []
    for s in out:
        host = credibility._host(s.get("url", ""), s.get("org", ""))
        key = (s.get("org"), s.get("url"))
        if key in seen or not s.get("note"):
            continue
        if host_count[host] >= 2:                # max 2 results per domain
            continue
        host_count[host] += 1
        seen.add(key)
        label, score = credibility.tier_source(s)
        s["tier"], s["_score"] = label, score
        s["_rel"] = _rel(s)
        s["_trusted"] = any(t in host for t in trusted) or s.get("is_factcheck", False)
        ded.append(s)

    # Relevance first (off-topic noise sinks), then trusted/published fact-checks,
    # then relevance magnitude, then credibility tier.
    ded.sort(key=lambda x: (x["_rel"] > 0.05, x["_trusted"], x["_rel"], x["_score"]), reverse=True)
    top = ded[:8]

    if full_doc:                                 # P1: read the actual articles, not snippets
        try:
            import fetch
            # Lean for the live path: fetch only the 2 most relevant in full (parallel,
            # short timeout) so the quality lift doesn't cost much latency.
            top = await fetch.enrich(top, " ".join(qs), max_fetch=2, n=5)
        except Exception:
            pass
    for s in top:
        s.pop("_score", None); s.pop("_rel", None); s.pop("_trusted", None)
    return top


def _assemble(r: dict, claims: list[str], sources: list[dict], domain: str) -> dict:
    cart = CARTRIDGES.get(domain, CARTRIDGES[DEFAULT_CARTRIDGE])
    verdict = str(r.get("verdict", "human")).lower()
    if verdict not in VALID:
        verdict = "human"
    try:
        conf = max(0, min(100, int(r.get("confidence", 50))))
    except Exception:
        conf = 50

    # Honor the model's own evidence-sufficiency self-check.
    if not r.get("evidence_sufficient", True) and verdict != "opinion":
        verdict = "human"

    # Calibrated abstention: high-stakes domains route to a human on low confidence.
    # For a calibrated Likert verdict we trust its margin for normal/conservative
    # domains — but for high-stakes ('fast': health/communal/disaster) we ALWAYS keep
    # the confidence floor, so a shaky verdict on a deadly rumor never ships.
    forced = False
    if verdict != "opinion" and conf < ABSTAIN_BELOW.get(cart.escalation, 55) \
            and (not r.get("_calibrated") or cart.escalation == "fast"):
        forced = verdict != "human"
        verdict = "human"

    # High-stakes corroboration gate: a DECISIVE verdict on a health/communal/disaster
    # claim must rest on at least one authoritative source (gov / WHO / a real
    # fact-checker), not just relevance-ranked open-web pages an attacker could seed.
    # Otherwise route to a human. This breaks the SEO/source-poisoning -> confident
    # verdict chain on exactly the domains where a wrong answer can get someone hurt.
    if cart.escalation == "fast" and verdict in ("true", "false", "misleading"):
        if not any((s.get("tier") == "authoritative") or s.get("is_factcheck") for s in (sources or [])):
            forced = True
            verdict = "human"

    meaning_en = r.get("meaning_en", "")
    meaning_hi = r.get("meaning_hi", "")
    counter_en = r.get("counter_en", "")
    counter_hi = r.get("counter_hi", "")
    if verdict == "human" and (forced or not meaning_en):
        meaning_en = meaning_en or "Viveka can't confirm this safely from its trusted sources. A human reviewer will check it before any verdict."
        meaning_hi = meaning_hi or "विवेका इसे अपने भरोसेमंद स्रोतों से पुष्टि नहीं कर सका। फैसले से पहले एक व्यक्ति इसे जाँचेगा।"
        counter_en = counter_en or "Please hold on before forwarding — this isn't confirmed yet. I'll share an update once it's checked."
        counter_hi = counter_hi or "कृपया भेजने से पहले रुकें — यह अभी पुष्ट नहीं है। पुष्टि होते ही मैं बताऊँगा/बताऊँगी।"

    return {
        "verdict": verdict, "confidence": conf, "claims": claims,
        "sources": sources or [],
        "meaningEn": meaning_en, "meaningHi": meaning_hi,
        "counterEn": counter_en, "counterHi": counter_hi,
        "weighNote": r.get("weigh_note", ""),
        "answers": r.get("answers", []),
        "probs": r.get("probs"),          # 4-label Likert dist for the report's confidence breakdown
        "escalate": verdict in ("misleading", "false") and cart.escalation == "fast",
        "domain": domain,
    }


def _basic_analysis(text: str) -> dict:
    """Minimal fallback if Gemma's analyze step returns empty — keep the check
    alive (one claim, a keyword query) instead of dropping the whole pipeline."""
    import re
    words = [w for w in re.findall(r"[A-Za-zऀ-ॿ]+", text) if len(w) > 3][:5]
    return {
        "language": "English", "domain": "general", "is_claim": True,
        "claims": [text[:200]],
        "questions": ["Is this claim true according to credible sources?"],
        "queries": [" ".join(words) or text[:60]],
    }


def _human_fallback(claims: list[str], sources: list[dict], domain: str) -> dict:
    """Graceful abstention built from the real claims + sources already retrieved
    (used when Gemma's reason step returns empty). Better than the generic offline."""
    return {
        "verdict": "human", "confidence": 35, "claims": claims, "sources": sources or [],
        "meaningEn": "Viveka found the relevant sources but couldn't reach a confident conclusion on its own, so a human reviewer will decide before any verdict.",
        "meaningHi": "विवेका को ज़रूरी स्रोत मिले पर वह खुद पक्का फैसला नहीं कर सका, इसलिए फैसले से पहले एक व्यक्ति इसे देखेगा।",
        "counterEn": "Please hold on before forwarding — this is still being checked. I'll share an update once it's confirmed.",
        "counterHi": "कृपया भेजने से पहले रुकें — इसे अभी जाँचा जा रहा है। पुष्टि होते ही मैं बताऊँगा/बताऊँगी।",
        "weighNote": "The evidence was inconclusive on its own, so this was routed to a human rather than guessing.",
        "escalate": False, "domain": domain,
    }


async def run_check_final(text: str, lang_pref: str = "en", image: str | None = None,
                          image_mime: str = "image/png") -> dict:
    """Drive the full pipeline and return just the final verdict result dict
    (drops the streamed trace). For non-streaming callers like the WhatsApp bot."""
    result, extracted = None, None
    async for ev in run_check(text, lang_pref, image=image, image_mime=image_mime):
        if ev.get("type") == "verdict":
            result = ev.get("result")
        elif ev.get("type") == "extracted":
            extracted = ev.get("text")
    if result is not None and extracted and not result.get("extractedText"):
        result["extractedText"] = extracted
    return result or {}


async def run_check(text: str, lang_pref: str = "en", image: str | None = None,
                    image_mime: str = "image/png"):
    # Image forwards: OCR the text out with Gemma first, then verify it like any
    # message. (Voice is transcribed in the browser and arrives as text.)
    if image:
        yield {"type": "extracting", "kind": "image"}
        try:
            import multimodal
            text = await asyncio.to_thread(multimodal.image_to_text, image, image_mime)
        except Exception:
            text = text or ""
        yield {"type": "extracted", "kind": "image", "text": text}

    text = (text or "").strip()
    if not text:
        yield {"type": "error", "message": "Couldn't read any text from that. Try pasting the message instead."}
        return

    # --- Antibody DB: a known rumor returns an instant verdict (no LLM call) ---
    import memory
    hit = await asyncio.to_thread(memory.match, text)
    if hit:
        e = hit["entry"]
        res = e["result"]
        yield {"type": "reading", "lang": "English", "domain": res.get("domain", "general")}
        await asyncio.sleep(0.4)
        # Honest payload: the match is real (report the cosine score); we do NOT ship
        # a fabricated "checked N times" usage count — that read as real telemetry.
        yield {"type": "matched", "known": True, "score": hit["score"]}
        await asyncio.sleep(0.9)
        yield {"type": "verdict", "result": {**res, "matched": True}}
        return

    if config.offline():
        async for ev in offline.run(text, lang_pref):
            yield ev
        return

    try:
        import analyze
        import verify

        # Start retrieval on raw-text keywords NOW, overlapping it with the analyze
        # Gemma call (which can take many seconds) so retrieval is mostly free.
        coarse_task = asyncio.create_task(_retrieve(_keywords(text), "general", cap=4, full_doc=False))
        try:
            d = await asyncio.to_thread(analyze.analyze, text)
        except Exception:
            d = _basic_analysis(text)  # analyze came back empty — keep going
        domain = d.get("domain", "general")
        yield {"type": "reading", "lang": d.get("language", "English"), "domain": domain}
        await asyncio.sleep(0.2)

        claims = d.get("claims") or []
        questions = d.get("questions") or []
        if not d.get("is_claim", True) or not claims:
            coarse_task.cancel()   # opinion/non-claim: no retrieval needed
            try:
                await coarse_task
            except BaseException:
                pass               # reap the cancelled task quietly
            yield {"type": "claims", "claims": claims or ["No verifiable factual claim — it reads as opinion or a joke."]}
            yield {"type": "sources", "sources": []}
            yield {"type": "verdict", "result": {
                "verdict": "opinion", "confidence": 75, "claims": claims or [], "sources": [],
                "meaningEn": "There's nothing factual here to check — it reads as an opinion or a joke.",
                "meaningHi": "इसमें जाँचने लायक कोई तथ्य नहीं है — यह राय या मज़ाक लगता है।",
                "counterEn": "", "counterHi": "",
                "weighNote": "No checkable factual claim was found.",
                "escalate": False, "domain": domain,
            }}
            return

        yield {"type": "claims", "claims": claims}
        if questions:
            yield {"type": "questions", "questions": questions}

        # Static parallel retrieval (InFact-style — the AVeriTeC 2024 winner's
        # design): one search per question + query, ALL fired at once. This is
        # both faster than a sequential agentic loop (2 Gemma calls total, not 4)
        # and the more accurate architecture. The agentic loop lives on for the
        # offline benchmark; the live product doesn't pay its latency.
        # The coarse retrieval has been running DURING analyze — collect it first.
        try:
            coarse = await coarse_task
        except Exception:
            coarse = []
        # Usually enough; only pay for a refined retrieval (model's targeted queries +
        # cartridge-trusted sources) when the overlapped pass came back thin.
        if len(coarse) >= 5:
            sources = coarse
        else:
            search_terms = list(d.get("queries") or [])
            if len(search_terms) < 2:
                search_terms += questions + [claims[0]]
            refined = await _retrieve(search_terms, domain, cap=5, full_doc=False)
            seen = {(s.get("org"), s.get("url")) for s in coarse}
            sources = (coarse + [s for s in refined if (s.get("org"), s.get("url")) not in seen])[:8]
        yield {"type": "sources", "sources": sources}

        try:
            r = await asyncio.to_thread(verify.verify, text, claims, questions, sources, domain)
            result = _assemble(r, claims, sources, domain)
        except Exception:
            # Reason came back empty (Gemma's non-deterministic thinking). Don't drop
            # to the generic offline path — abstain to a human using the REAL claims and
            # sources we already retrieved. Coherent trace, and it still gets remembered.
            result = _human_fallback(claims, sources, domain)

        # Two-mode escalation: a single pass would abstain here (verify's own
        # confidence is unreliable — it reads ~100% on everything, ECE ~0.33). So
        # before bothering a human, get a second opinion from the 3-lens debate
        # panel, and trust it ONLY when the panel actually agrees (agreement is a
        # real, calibrated confidence signal where self-reported confidence is not).
        if result.get("verdict") == "human" and sources:
            try:
                import debate
                yield {"type": "escalating", "to": "panel"}
                loop_result = {"evidence": sources, "qa": result.get("answers", [])}
                v = await asyncio.to_thread(debate.debate_decide, text, loop_result)
                agree = v.get("agreement") or 0
                pv = _DEBATE_TO_PRODUCT.get(str(v.get("label", "")).lower())
                yield {"type": "panel", "agreement": agree, "label": v.get("label"), "split": v.get("panel_split")}
                if agree >= 0.67 and pv and pv != "human":
                    result["verdict"] = pv
                    result["confidence"] = int(v.get("confidence", result.get("confidence", 60)))
                    result["panelAgreement"] = agree
                    result["weighNote"] = ((result.get("weighNote", "") + " A 3-lens review panel "
                                            f"reached this with {int(agree*100)}% agreement.").strip())
            except Exception:
                pass  # escalation is best-effort; the human-route still stands

        await asyncio.to_thread(memory.remember, text, result)  # build immunity
        yield {"type": "verdict", "result": result}
    except Exception as e:
        # Graceful degradation — never crash the stream.
        async for ev in offline.run(text, lang_pref, error=str(e)):
            yield ev
