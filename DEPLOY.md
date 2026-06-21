# Deploying Viveka ($0, free tiers)

Two pieces: the **engine** (FastAPI, on Render) and the **web app** (Vite SPA, on
Vercel). The WhatsApp last-mile is optional and points at the same engine.

## 1. Engine → Render (free)

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → select the repo. It reads [`render.yaml`](render.yaml).
3. After the first deploy, open the service → **Environment** and set:
   - `GEMINI_API_KEY` — your free key from [aistudio.google.com](https://aistudio.google.com)
   - `GOOGLE_FACTCHECK_API_KEY` — optional (extra evidence source)
4. Confirm it's up: `GET https://<your-engine>.onrender.com/api/health` → `{"ok": true, ...}`.

> Free Render sleeps after inactivity; the first request after idle takes a few
> seconds to wake. Fine for a demo.

## 2. Web app → Vercel (free)

1. Vercel → **New Project** → select the repo, set **Root Directory** to `frontend`.
   It reads [`frontend/vercel.json`](frontend/vercel.json) (framework auto-detected).
2. Add an env var: `VITE_ENGINE_URL = https://<your-engine>.onrender.com`
3. Deploy. The SPA calls the engine at that origin; with no engine reachable it
   falls back to the seeded offline demo, so it never shows a blank screen.

## 3. (Optional) WhatsApp last-mile

The engine already exposes `GET/POST /webhook`. To connect it:

1. Create a Meta app → add the **WhatsApp** product → get a phone-number id and a
   token.
2. On the Render engine, set `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, and
   `WHATSAPP_VERIFY_TOKEN` (any string; default `viveka-verify`).
3. In Meta's webhook config, set the callback URL to
   `https://<your-engine>.onrender.com/webhook` and the verify token to match.
   Subscribe to `messages`.
4. Forward any suspicious message to the number → the engine checks it and replies
   with a verdict, sources, and a forward-ready counter-message.

> User-initiated messages (someone forwarding a rumor to you) are free and
> unlimited on the Cloud API, and a single-purpose verification service is allowed
> under Meta's 2026 policy — so this stays $0.

## Local dev

```bash
# engine
cd backend && python -m venv .venv && . .venv/Scripts/activate   # (Windows)
pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# web app (separate terminal) — Vite proxies /api -> localhost:8000
cd frontend && npm install && npm run dev
```
