# Viveka architecture

One engine. Many input doors. A human as the safety valve. Graceful degradation everywhere. Everything on free tiers ($0).

A rendered diagram is in [`architecture.svg`](architecture.svg). The text version:

```
 ┌──────────────┐
 │   INPUT       │   text  ·  image (OCR)  ·  voice (browser ASR)        any language
 └──────┬───────┘
        │
        ▼
 ┌───────────────────────────── KNOWN RUMOUR? ─────────────────────────────┐
 │  antibody memory  (embedding match)                                       │
 │     hit  ─────────────────────────────────────────────►  instant verdict  │   no LLM call
 │     miss ▼                                                                 │
 └───────────────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1 ANALYZE     │ → │ 2 RETRIEVE    │ → │ 3 REASON      │ → │ 4 CALIBRATE   │
 │ claims +      │   │ web · Wiki ·  │   │ Likert-softmax│   │ domain-aware  │
 │ questions     │   │ Fact Check    │   │ over 4 labels │   │ abstain margin│
 │ (Gemma 4)     │   │ (full-doc)    │   │ (Gemma 4)     │   │               │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                                   │
                       ┌───────────────────────────────────────────┤
                       ▼                                            ▼
              ┌──────────────────┐                        ┌──────────────────┐
              │ HIGH-STAKES GATE  │  no authoritative      │  CONFIDENT?       │
              │ health/communal/  │  source ──────────────►│   yes ▼   no ─────┼──► HUMAN REVIEW
              │ disaster          │                        │                   │
              └──────────────────┘                        └────────┬─────────┘
                                                                    │
                                                                    ▼
 ┌──────────────────────────── OUTPUT: VERIFICATION REPORT ────────────────────────────┐
 │  verdict (1 of 5)  ·  calibrated confidence  ·  clickable evidence  ·  correction     │
 │  ACT (gated, region-adaptive):  warn the group · report (IN: Chakshu/1930/PIB ·       │
 │                                  US: FTC/IC3/FCC) · protect                            │
 └───────────────────────────────────────────────────────────────────────────────────────┘

 fallback: any stage fails → "Requires human review"   ·   no key → canned reasoning (demo-safe)
```

## The five stages

1. **Analyze** (Gemma 4): break the forward into atomic, checkable claims and the questions whose answers would settle them. This is what separates a verifier from "retrieve and guess."
2. **Retrieve** (keyless): fire web search + Wikipedia + Google Fact Check in parallel, rank by relevance, read the top sources full-document (not snippets).
3. **Reason** (Gemma 4): rate all four AVeriTeC verdicts 1-5 and softmax them, instead of trusting a single self-reported confidence that reads ~98% on everything.
4. **Calibrate and abstain**: a domain-aware margin decides whether to commit or route to a human. High-stakes domains keep a confidence floor.
5. **Act** (gated): only a confident verdict unlocks warn / report; an abstained verdict refuses to act and routes to a human.

## Why these choices

- **Static parallel retrieval** (the InFact design, AVeriTeC 2024 winner) is both faster and more accurate than a sequential agentic loop for the live product.
- **Antibody memory** answers known rumours instantly with no LLM call, and is the $0-friendly path under a congested free tier.
- **Two modes, one engine:** `product` (5 labels, abstains to a human) and `benchmark` (4 labels, commits, for AVeriTeC scoring) share all the reasoning code.

## Stack (all free tier)

FastAPI · Gemma 4 (`gemma-4-31b-it`, Google API) · `gemini-embedding-001` · trafilatura · rank-bm25 · ddgs · React + Vite + Tailwind. No paid service anywhere.
