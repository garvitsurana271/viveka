"""Viveka engine — FastAPI app. Streams the verification trace as SSE."""
from __future__ import annotations
import json
import time
from collections import deque, defaultdict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
import config
import engine

app = FastAPI(title="Viveka engine", version="0.1.0")

# Per-IP rate limit on the cost-bearing endpoint, so one client can't drain the
# free Gemma quota (1500/day) and take the public demo dark. Generous enough that
# real use never hits it; an in-memory sliding window (good for a single instance).
_RL_MAX, _RL_WINDOW = 20, 60.0
_rl_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if request.url.path == "/api/check":
        # Behind a proxy (Render/Vercel) request.client.host is the proxy IP and would
        # put every visitor in one bucket — use the real client from X-Forwarded-For.
        xff = request.headers.get("x-forwarded-for", "")
        ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?")
        now = time.monotonic()
        q = _rl_hits[ip]
        while q and now - q[0] > _RL_WINDOW:
            q.popleft()
        if len(q) >= _RL_MAX:
            return JSONResponse({"detail": "Too many checks — please slow down a moment."}, status_code=429)
        q.append(now)
    return await call_next(request)

# Demo: allow any origin (the SPA may be on Vercel, localhost, etc.).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckIn(BaseModel):
    # Caps stop a giant payload from OOMing the process or draining the Gemma quota.
    text: str = Field("", max_length=8000)
    lang: str = "en"
    image: str | None = Field(None, max_length=8_000_000)   # ~6 MB decoded
    image_mime: str = "image/png"


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "offline": config.offline(),
        "provider": config.LLM_PROVIDER,
        "model": config.GEMINI_MODEL if config.LLM_PROVIDER == "gemini" else config.LLM_PROVIDER,
        "factcheck_key": bool(config.GOOGLE_FACTCHECK_API_KEY),
        "whatsapp": config.whatsapp_ready(),
    }


# --- WhatsApp last-mile webhook (forward a message -> get a verdict) ----------
@app.get("/webhook")
def whatsapp_verify(request: Request):
    """Meta's verification handshake."""
    import whatsapp
    q = request.query_params
    challenge = whatsapp.verify_challenge(
        q.get("hub.mode", ""), q.get("hub.verify_token", ""), q.get("hub.challenge", ""))
    if challenge is not None:
        return PlainTextResponse(challenge)
    return PlainTextResponse("forbidden", status_code=403)


@app.post("/webhook")
async def whatsapp_inbound(request: Request):
    """Inbound message -> run the engine -> reply. Always 200 so Meta doesn't retry."""
    import whatsapp
    try:
        body = await request.json()
        await whatsapp.handle_inbound(body)
    except Exception:
        pass
    return {"status": "ok"}


@app.get("/api/pulse")
def pulse():
    """The real rumors in Viveka's memory — what it has seen and learned."""
    import memory
    return {"rumors": memory.pulse_view()}


@app.post("/api/check")
async def check(inp: CheckIn):
    async def gen():
        async for ev in engine.run_check(inp.text, inp.lang, image=inp.image, image_mime=inp.image_mime):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- Serve the built SPA so one service hosts the whole product ----------------
# The frontend is pre-built into backend/static (committed), so the engine serves
# both the UI and the /api routes from a single origin. Registered LAST, so every
# /api and /webhook route above is matched first; the catch-all only handles GET.
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_DIST = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_DIST):
    _assets = os.path.join(_DIST, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/")
    def _spa_index():
        return FileResponse(os.path.join(_DIST, "index.html"))

    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str):
        f = os.path.join(_DIST, full_path)
        if os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(os.path.join(_DIST, "index.html"))
