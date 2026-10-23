"""End-to-end checks against a RUNNING gateway (real llama-server or the mock).

    python tests/smoke_test.py                      # basic checks
    python tests/smoke_test.py --users 4            # also: 4 simultaneous users, each must get only their own answer
    python tests/smoke_test.py --users 6 --expect-busy   # use with a low MAX_INFLIGHT to see HTTP 429

Note: with the mock server each answer echoes the question; with a real model the
"own answer" check is skipped because a real model will not echo the tag.
"""
import argparse
import os
import sys
import threading

import requests

GATEWAY = os.getenv("GATEWAY_URL", "http://127.0.0.1:8000").rstrip("/")
KEY = os.getenv("GATEWAY_KEY", "change-me")
results = []


def check(name, ok, extra=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {extra}")


def chat(text, key=KEY, session="smoke", body=None):
    payload = body or {"messages": [{"role": "user", "content": text}], "max_tokens": 40}
    return requests.post(f"{GATEWAY}/chat", json=payload, stream=True, timeout=120,
                         headers={"x-api-key": key, "x-session-id": session})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=0)
    ap.add_argument("--expect-busy", action="store_true")
    ap.add_argument("--real-model", action="store_true", help="skip the echo check")
    args = ap.parse_args()

    h = requests.get(f"{GATEWAY}/health", timeout=5).json()
    check("health reports gateway ok", h.get("gateway") == "ok", str(h))
    check("model server reachable", h.get("model_server") == "ok")

    r = chat("hi", key="wrong")
    check("wrong API key -> 401", r.status_code == 401)
    r = chat("x", body={"messages": [{"role": "assistant", "content": "only assistant"}]})
    check("no user message -> 422", r.status_code == 422)

    r = chat("hello gateway")
    text = "".join(r.iter_content(chunk_size=None, decode_unicode=True)) if r.status_code == 200 else ""
    check("single chat -> 200 with text", r.status_code == 200 and len(text) > 0, repr(text[:60]))
    check("X-Request-ID header present", bool(r.headers.get("X-Request-ID")))

    if args.users:
        out = {}

        def worker(i):
            tag = f"USER{i}TAG"
            resp = chat(f"question from {tag}", session=f"user-{i}")
            body = "".join(resp.iter_content(chunk_size=None, decode_unicode=True)) if resp.status_code == 200 else ""
            out[i] = (resp.status_code, tag, body)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.users)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        codes = [v[0] for v in out.values()]
        print("status codes:", codes)
        if args.expect_busy:
            check("some requests rejected with 429 when busy", 429 in codes)
            check("accepted requests still completed", 200 in codes)
        else:
            check(f"all {args.users} concurrent users got 200", all(c == 200 for c in codes))
        if not args.real_model:
            ok = all(v[1] in v[2] and not any(f"USER{j}TAG" in v[2] for j in range(args.users) if j != i)
                     for i, v in out.items() if v[0] == 200)
            check("each user received only their own answer", ok)

    stats = requests.get(f"{GATEWAY}/stats", headers={"x-api-key": KEY}, timeout=5).json()
    print("stats:", {k: v for k, v in stats.items() if k != "llama_slots"})
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
