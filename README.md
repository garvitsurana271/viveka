# Viveka: discern before you forward

An AI that checks suspicious chat forwards **before** they spread. Paste a
message (text / image / voice) in any major Indian language; Viveka breaks it
into claims, **searches trusted sources in a multi-hop loop**, returns a
calibrated verdict with citations and a forward-ready correction, or routes it
to a human when it isn't sure. It is **benchmarked on AVeriTeC**, the academic
standard for claim verification, so the quality is a number, not a vibe.

Built for the **USAII Global AI Hackathon 2026** (High School track, Community →
Rumor vs. Reality). Surfaces: **Check** (the verifier), **Review** (human in the
loop), **Pulse** (what's spreading now), plus a **WhatsApp** last-mile.

## Architecture
```
frontend (React + Vite + Tailwind)         backend (FastAPI, Python)
  Check / Review / Pulse           --SSE-->  /api/check   (streams the trace)
  live "watch it think" trace                /webhook     (WhatsApp last-mile)
  (multi-hop + panel escalation)             engine.py  ── orchestrator
                                               ├─ analyze.py   claims · questions · queries · tactics ─ Gemma 4
                                               ├─ agentic.py   bounded multi-hop retrieve→read→re-search loop
                                               │                 (ddgs · Wikipedia · Google Fact Check)
                                               ├─ verify.py    grounded verdict + self-check          ─ Gemma 4
                                               ├─ debate.py    3-lens panel + judge (escalation)      ─ Gemma 4
                                               └─ calibrate/abstain → human when the panel disagrees
                                             memory.py = antibody DB (known rumors answered instantly)
                                             offline.py = canned demo (no key, $0)
```
**One engine, two modes:** `product` keeps the 5-label taxonomy and abstains to a
human; `benchmark` commits to AVeriTeC's 4 labels for scoring. **Graceful
degradation:** every failing stage routes to "needs human check"; with no LLM key
the engine serves faithful canned reasoning, so the demo can't hard-fail.

## Benchmarked on AVeriTeC (with the caveats stated up front)

We report on a **balanced 25-per-class slice** of AVeriTeC dev, balanced on purpose
so macro-F1 reflects all four verdict classes equally instead of being inflated by
AVeriTeC's natural ~61%-Refuted majority. Read the numbers with three caveats:

1. **0.733 is gold-evidence, label-only.** The model is handed good evidence and must
   reach the right label. It is **not** the official Ev2R-conditioned "AVeriTeC score"
   (top published systems land around 0.48), so it is not a leaderboard ranking.
2. **0.398 is the live end-to-end number** (the full pipeline retrieving its own
   evidence, n=40 balanced). It is lower because retrieval is the hard part, and we
   publish it rather than hide it.
3. **The engine abstains on ~36% even with perfect gold evidence** (its high-stakes
   confidence floor declining to commit), and ~15% live. That is the safety posture
   we chose: a cautious verifier, not a confident-wrong one. n is small (100 / 40); read
   the decimals as directional, not leaderboard-precise.

Gold-evidence reasoning ablation (balanced n=100):

| Method | Accuracy | Macro-F1 | Note |
|---|---|---|---|
| **Likert-softmax + dynamic exemplars** | **0.730** | **0.733** | best, the recipe the product ships |
| + Likert-softmax (alone) | 0.700 | 0.700 | fixed the over-abstention, +0.064 over baseline |
| Single-pass (baseline) | 0.640 | 0.636 | plain prompt |
| + few-shot (Conflicting-weighted) | 0.620 | 0.623 | lifted Conflicting recall but net-negative, measured and not shipped |
| + 3-lens debate panel | 0.630 | 0.625 | a wash on accuracy, but its agreement is a calibrated signal |

**The real finding is calibration.** The model's self-reported confidence is useless:
ECE **0.327**, it says ~98% on nearly everything and is ~65% right. We recalibrate the
displayed confidence (ECE drops to about **0.21**, still imperfect, which is exactly why
we abstain), and product mode abstains on **panel disagreement**, a signal that actually
separates right from wrong (about **70%** accurate when the 3 lenses agree, **39%** when
they split), not on a number the model invented. Full method in
[`backend/eval/METHODOLOGY.md`](backend/eval/METHODOLOGY.md); the [System Card](SYSTEM-CARD.md)
lists every limitation.

## Run it

**Backend** (Python 3.11+):
```bash
cd backend
py -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # (Windows)
# mac/linux: python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app:app --port 8000
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev    # http://localhost:5173 (proxies /api -> :8000)
```

Open the dev URL → **Check** → pick a sample → **Check this message**.

### Live engine (free)
Without a key it runs offline (canned). For real reasoning: get a free key at
https://aistudio.google.com/apikey, put `GEMINI_API_KEY=...` in `backend/.env`
(defaults to **Gemma 4**, `gemma-4-31b-it`), restart. `GET /api/health` shows
`"offline": false`. Optional: `GOOGLE_FACTCHECK_API_KEY` adds fact-check retrieval.

### Evaluate it
```bash
cd backend
python eval/averitec_runner.py --split dev --n 100 --track gold --workers 4   # baseline
python eval/averitec_runner.py --split dev --n 100 --track golddebate         # debate
python eval/calibration.py eval/reports/baseline_dev_n100_gold.json           # ECE
```
Every Gemma call is disk-cached, so re-runs only pay for prompts that changed.

### Deploy ($0)
Render (engine) + Vercel (SPA) + optional WhatsApp (see [`DEPLOY.md`](DEPLOY.md)).

## Status
- ✅ Research-grade engine: bounded agentic multi-hop retrieval, **AVeriTeC-benchmarked**
- ✅ Multi-agent debate panel + agreement-based calibrated abstention
- ✅ Three surfaces + streamed multi-hop trace; bilingual (English + Hindi gloss)
- ✅ WhatsApp last-mile (forward a message → verdict); image (Gemma OCR) + voice (Web Speech)
- ✅ Offline mode ($0, always works) + graceful degradation; deploy configs

See `UX-SPEC.md`, `DESIGN-TOKENS.md`, `RESEARCH.md`, `CHALLENGE-BRIEF.md`,
`backend/eval/METHODOLOGY.md`.
