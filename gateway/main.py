"""FastAPI gateway in front of llama.cpp's llama-server.

Responsibilities (llama-server itself only does inference):
  * API-key check, so only the Streamlit frontend (or you) can call it
  * per-session rate limit and a cap on requests in flight (HTTP 429 when busy)
  * input trimming and clamping (history length, max_tokens, temperature)
  * streaming tokens from llama-server to the caller over the same connection
  * a request id and one log line per request (time to first token, tokens, duration)

Run:  uvicorn gateway.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ----------------------------------------------------------------- config
LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:8080").rstrip("/")
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "change-me")
MAX_INFLIGHT = int(os.getenv("MAX_INFLIGHT", "12"))
MAX_TOKENS_CAP = int(os.getenv("MAX_TOKENS_CAP", "512"))
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "12"))
MAX_CHARS_PER_MESSAGE = int(os.getenv("MAX_CHARS_PER_MESSAGE", "4000"))
MODEL_LABEL = os.getenv("MODEL_LABEL", "local model")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful, concise assistant running locally on an NVIDIA Jetson Orin Nano.",
)
TEMPERATURE_RANGE = (0.0, 1.2)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gateway")


# ------------------------------------------------------------------ state
class Stats:
    """Counters shown by GET /stats. Plain ints are safe: asyncio runs on one thread."""

    def __init__(self) -> None:
        self.started = time.time()
        self.inflight = 0
        self.total = 0
        self.completed = 0
        self.rejected_busy = 0
        self.rejected_rate = 0
        self.upstream_errors = 0


stats = Stats()
_rate_log: dict[str, deque[float]] = defaultdict(deque)


def _allow(session_id: str) -> bool:
    """Sliding-window limiter: at most RATE_LIMIT_PER_MIN requests per session per 60 s."""
    now = time.monotonic()
    window = _rate_log[session_id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MIN:
        return False
    window.append(now)
    if len(_rate_log) > 5000:  # forget sessions that have gone quiet
        for key in [k for k, w in _rate_log.items() if not w or now - w[-1] > 60]:
            _rate_log.pop(key, None)
    return True


# --------------------------------------------------------------- schemas
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    max_tokens: int = 256
    temperature: float = 0.7


# -------------------------------------------------------------------- app
@asynccontextmanager
async def lifespan(app: FastAPI):
    if GATEWAY_KEY == "change-me":
        log.warning("GATEWAY_KEY is still the default. Set a real secret in .env before exposing anything.")
    # One shared client. No read timeout: a long generation is normal. 5 s to connect.
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5.0))
    log.info("gateway up: llama-server=%s max_inflight=%d", LLAMA_URL, MAX_INFLIGHT)
    yield
    await app.state.client.aclose()


app = FastAPI(title="Jetson Edge LLM Gateway", lifespan=lifespan)


def _check_key(x_api_key: str | None) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, GATEWAY_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.get("/health")
async def health():
    """Open endpoint (no key): is the gateway up, and is llama-server reachable?"""
    model_ok = False
    try:
        r = await app.state.client.get(f"{LLAMA_URL}/health", timeout=3.0)
        model_ok = r.status_code == 200
    except httpx.HTTPError:
        pass
    return {
        "gateway": "ok",
        "model_server": "ok" if model_ok else "down",
        "model": MODEL_LABEL,
        "inflight": stats.inflight,
        "max_inflight": MAX_INFLIGHT,
    }


@app.get("/stats")
async def get_stats(x_api_key: str | None = Header(default=None)):
    _check_key(x_api_key)
    slots = None
    try:  # /slots is optional in llama-server; ignore if absent or disabled
        r = await app.state.client.get(f"{LLAMA_URL}/slots", timeout=3.0)
        if r.status_code == 200:
            slots = r.json()
    except (httpx.HTTPError, ValueError):
        pass
    return {
        "uptime_s": round(time.time() - stats.started),
        "inflight": stats.inflight,
        "total_requests": stats.total,
        "completed": stats.completed,
        "rejected_busy": stats.rejected_busy,
        "rejected_rate_limit": stats.rejected_rate,
        "upstream_errors": stats.upstream_errors,
        "llama_slots": slots,
    }


@app.post("/chat")
async def chat(
    req: ChatRequest,
    x_api_key: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
):
    """Stream a reply as plain text. Each caller gets only the tokens for its own request."""
    _check_key(x_api_key)
    session = (x_session_id or "anonymous")[:64]
    request_id = uuid.uuid4().hex[:8]
    stats.total += 1

    if not _allow(session):
        stats.rejected_rate += 1
        raise HTTPException(status_code=429, detail="Too many messages. Wait a moment and try again.",
                            headers={"Retry-After": "30"})
    # Check and increment with no await in between, so two requests can never both take the last slot.
    if stats.inflight >= MAX_INFLIGHT:
        stats.rejected_busy += 1
        raise HTTPException(status_code=429, detail="The server is busy. Try again in a few seconds.",
                            headers={"Retry-After": "5"})

    # Keep the newest messages; the model must see a user turn first (after any system prompt).
    msgs = [{"role": m.role, "content": m.content[:MAX_CHARS_PER_MESSAGE]} for m in req.messages]
    msgs = [m for m in msgs if m["role"] != "system"][-MAX_MESSAGES:]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    if not msgs or msgs[-1]["role"] != "user":
        raise HTTPException(status_code=422, detail="The last message must come from the user.")
    msgs.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    payload = {
        "messages": msgs,
        "stream": True,
        "max_tokens": max(1, min(req.max_tokens, MAX_TOKENS_CAP)),
        "temperature": min(max(req.temperature, TEMPERATURE_RANGE[0]), TEMPERATURE_RANGE[1]),
    }

    stats.inflight += 1
    client: httpx.AsyncClient = app.state.client
    try:
        upstream = await client.send(
            client.build_request("POST", f"{LLAMA_URL}/v1/chat/completions", json=payload),
            stream=True,
        )
    except httpx.HTTPError as exc:
        stats.inflight -= 1
        stats.upstream_errors += 1
        log.error("req=%s session=%s cannot reach llama-server: %r", request_id, session[:8], exc)
        raise HTTPException(status_code=503, detail="The model server is not reachable. Is llama-server running?")
    if upstream.status_code != 200:
        body = (await upstream.aread())[:300]
        await upstream.aclose()
        stats.inflight -= 1
        stats.upstream_errors += 1
        log.error("req=%s llama-server returned %s: %s", request_id, upstream.status_code, body)
        raise HTTPException(status_code=502, detail=f"The model server returned an error ({upstream.status_code}).")

    async def relay():
        t0 = time.perf_counter()
        first: float | None = None
        tokens = 0
        status = "ok"
        try:
            async for line in upstream.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    choices = json.loads(data).get("choices") or []
                except json.JSONDecodeError:
                    continue
                if not choices:
                    continue
                text = (choices[0].get("delta") or {}).get("content")
                if text:
                    if first is None:
                        first = time.perf_counter() - t0
                    tokens += 1
                    yield text
        except httpx.HTTPError as exc:
            status = "upstream_error"
            stats.upstream_errors += 1
            log.error("req=%s stream broke: %r", request_id, exc)
            yield "\n\n[The connection to the model server was lost.]"
        except asyncio.CancelledError:
            status = "client_disconnected"  # browser closed: closing upstream lets llama-server free the slot
            raise
        finally:
            with contextlib.suppress(Exception):
                await upstream.aclose()
            stats.inflight -= 1
            if status == "ok":
                stats.completed += 1
            log.info(
                "req=%s session=%s status=%s ttft=%s tokens=%d total=%.2fs inflight=%d",
                request_id, session[:8], status,
                f"{first:.2f}s" if first is not None else "n/a",
                tokens, time.perf_counter() - t0, stats.inflight,
            )

    return StreamingResponse(
        relay(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Request-ID": request_id, "Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
