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

# --- Quota protection for the public demo -------------------------------------
# /api/check is the only endpoint that can spend the free Gemma quota (~1500/day).
# The real guard is the two GLOBAL caps (per-minute + per-day): they count EVERY
# call regardless of source IP, so they cannot be bypassed by spoofing the
# X-Forwarded-For header (the usual trick) or by rotating through many IPs — the
# whole demo simply cannot call Gemma faster than the global rate, nor more than the
# global daily budget, no matter what the client sends. The per-IP caps are
# best-effort fairness layered on top. All counters are in-memory (fine for one
# free-tier instance) and reset on restart / at UTC midnight. Tune any value via env
# vars on Render (RL_PER_MIN / RL_PER_DAY / RL_GLOBAL_MIN / RL_GLOBAL_DAY), no code change.
import os
_RL_PER_MIN    = int(os.getenv("RL_PER_MIN", "6"))        # per-IP, sliding 60s
_RL_PER_DAY    = int(os.getenv("RL_PER_DAY", "20"))       # per-IP, per UTC day
_RL_GLOBAL_MIN = int(os.getenv("RL_GLOBAL_MIN", "40"))    # WHOLE demo, sliding 60s (IP-independent)
_RL_GLOBAL_DAY = int(os.getenv("RL_GLOBAL_DAY", "400"))    # WHOLE demo, per UTC day (IP-independent)

_rl_min: dict[str, deque] = defaultdict(deque)   # per-IP recent timestamps
_rl_day: dict[str, int] = defaultdict(int)       # per-IP count today
_rl_gmin: deque = deque()                        # whole-demo recent timestamps
_rl_global = {"day": "", "n": 0}                 # whole-demo count today


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if request.url.path == "/api/check":
        now = time.monotonic()
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if _rl_global["day"] != day:                 # new UTC day -> reset daily counters
            _rl_global["day"], _rl_global["n"] = day, 0
            _rl_day.clear(); _rl_min.clear()

        # 1) GLOBAL caps — IP-independent, so spoofing X-Forwarded-For / rotating IPs
        #    cannot get around them. This is the actual quota guard.
        while _rl_gmin and now - _rl_gmin[0] > 60.0:
            _rl_gmin.popleft()
        if len(_rl_gmin) >= _RL_GLOBAL_MIN:
            return JSONResponse({"detail": "The live demo is busy right now — please try again in a minute."}, status_code=429)
        if _rl_global["n"] >= _RL_GLOBAL_DAY:
            return JSONResponse({"detail": "The live demo has hit its daily limit (protecting a free-tier quota). Please try again tomorrow."}, status_code=429)

        # 2) Per-IP fairness (best-effort — X-Forwarded-For can be spoofed, but the
        #    global caps above already bound total spend regardless of that).
        xff = request.headers.get("x-forwarded-for", "")
        ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?")
        q = _rl_min[ip]
        while q and now - q[0] > 60.0:
            q.popleft()
        if len(q) >= _RL_PER_MIN:
            return JSONResponse({"detail": "Too many checks in a minute — please slow down a moment."}, status_code=429)
        if _rl_day[ip] >= _RL_PER_DAY:
            return JSONResponse({"detail": "You've reached today's limit for this live demo. Try again tomorrow, or watch the demo video."}, status_code=429)

        # Passed every gate -> count it (blocked requests are not counted).
        _rl_gmin.append(now); _rl_global["n"] += 1
        q.append(now); _rl_day[ip] += 1
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
_INDEX = os.path.join(_DIST, "index.html")
if os.path.isfile(_INDEX):
    _assets = os.path.join(_DIST, "assets")
    if os.path.isdir(_assets):
        # Starlette's StaticFiles resolves and confines paths to the directory, so
        # the built JS/CSS is served with no path-traversal surface.
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/favicon.svg")
    def _favicon():
        return FileResponse(os.path.join(_DIST, "favicon.svg"))

    @app.get("/")
    def _spa_index():
        return FileResponse(_INDEX)

    # SPA catch-all: every other GET returns the app shell. Crucially, NO request
    # input is ever joined to a filesystem path here, so there is no path traversal
    # (a request like /../../config.py just returns index.html).
    @app.get("/{full_path:path}")
    def _spa_fallback(full_path: str):
        return FileResponse(_INDEX)
