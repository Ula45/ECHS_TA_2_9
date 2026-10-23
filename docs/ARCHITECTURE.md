# Architecture

```
Browser tab ──websocket──> Streamlit session ──HTTP──> FastAPI request ──HTTP──> llama-server ──> GPU
   (A, B, C...)             (one per tab)               (one per message)         (task -> slot)
```

## Why three layers

| Layer | Why it exists |
|---|---|
| **llama-server** | Does only inference: scheduling, batching, KV cache, GPU. Has no real user management, so it stays on localhost |
| **FastAPI gateway** | The control point: API key, rate limit, cap on requests in flight, trimming, logging, clean error messages. Uses `async` so waiting for the model never blocks other connections |
| **Streamlit** | The interface. Each browser tab is a separate session with private `st.session_state`. It holds the API key server-side, so visitors never see it |

## Life of one request

1. A user submits a message. Streamlit runs the script for **that tab's session**.
2. The script POSTs to `/chat` with `x-api-key` and the tab's `x-session-id`. The connection stays open.
3. The gateway checks the key, the session's rate limit and the in-flight cap (`429` if busy). It trims the history, adds the system prompt, clamps `max_tokens` and temperature, and generates a **request id**.
4. It opens a streaming connection to llama-server's `/v1/chat/completions`.
5. llama-server creates a **task**, assigns it to a **free slot** (or queues it), and processes the prompt (prefill).
6. Each decode step, llama-server batches the next token of **every active slot** into one pass over the model weights (continuous batching) and sends each token to its own task's connection.
7. The gateway extracts the text from each streamed chunk and writes it to the caller's response. Streamlit displays it as it arrives.
8. When the reply ends (or the browser disconnects), the gateway closes the upstream connection, llama-server frees the slot, and the gateway logs one line:
   `req=<id> session=<id> status=ok ttft=0.42s tokens=87 total=15.1s inflight=1`

## Identity: where ids appear

- **Connection**: decides who receives the tokens. No lookup is needed because the answer is written to the connection the question came from.
- **Session id** (`x-session-id`): created per browser tab; used for rate limiting and log correlation.
- **Request id**: created per message by the gateway; returned in `X-Request-ID` and logged.
- **Task id / slot number**: internal to llama-server. A slot is **temporary**. It is not "user B's slot"; the next request from anyone can land in any free slot. That is why the UI resends recent history with every message: the model keeps no memory between requests.

## Slots, context and memory

- `--parallel N` creates N slots that share **one copy of the weights**.
- `-c` is the **total** context, divided between slots. `-c 4096 --parallel 2` gives each user 2048 tokens (prompt plus reply).
- KV-cache memory grows with total context. For Llama 3.2 3B with `q8_0` K and V, about 61 KB per token: 28 layers x 8 KV heads x 128 dims x 2 (K and V) x about 1.06 bytes.
- More requests than slots wait in llama-server's queue. The gateway's `MAX_INFLIGHT` limits how many may wait before it answers `429`.

## Throughput and latency

Token generation is limited by memory bandwidth: every token needs a pass over the weights. Continuous
batching lets one pass advance several conversations, so **total tokens/s can rise with more users while
each user's tokens/s falls**. Prefill (reading the prompt) is compute-heavy, so a long prompt can delay
other users' tokens briefly. Measure with `benchmarks/bench.py`.

## Network and exposure

Only Streamlit (port 8501) is meant to be reachable. The gateway (8000) and llama-server (8080) bind to
`127.0.0.1`. A Cloudflare quick tunnel makes an outbound connection from the Jetson to Cloudflare and
forwards visitors to `localhost:8501`, so no port forwarding is needed. Traffic passes through Cloudflare's servers.
