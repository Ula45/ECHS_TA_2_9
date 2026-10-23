"""A tiny stand-in for llama-server so the gateway and UI can be tested without a GPU.

It speaks the same OpenAI-style streaming protocol, echoes the user's message back
(so tests can prove each caller receives only its own answer), and limits how many
requests are served at once (MOCK_SLOTS) the way llama-server's --parallel does.

Run:  MOCK_SLOTS=2 uvicorn tests.mock_llama:app --port 8080
"""
import asyncio
import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

SLOTS = int(os.getenv("MOCK_SLOTS", "2"))
DELAY = float(os.getenv("MOCK_TOKEN_DELAY", "0.03"))
app = FastAPI()
_slots = asyncio.Semaphore(SLOTS)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    last_user = [m["content"] for m in body["messages"] if m["role"] == "user"][-1]
    words = f"You said: {last_user} . This is the mock model answering.".split()
    words = words[: body.get("max_tokens", 50)]

    async def gen():
        async with _slots:  # waits here when all "slots" are busy, like llama-server's queue
            for w in words:
                await asyncio.sleep(DELAY)
                yield "data: " + json.dumps({"choices": [{"delta": {"content": w + " "}}]}) + "\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
