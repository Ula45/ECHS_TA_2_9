"""Concurrency benchmark. Measures what each simulated user experiences.

Two targets:
  --target llama    talk to llama-server directly (OpenAI streaming API). Best for tokens/sec:
                    each streamed delta is about one token.
  --target gateway  go through the FastAPI gateway (end-to-end latency, includes queueing,
                    rate limits and 429s). Chunk counts are approximate because TCP may merge tokens.

Examples:
  python benchmarks/bench.py --label 3b-1slot --users 1 2 4
  python benchmarks/bench.py --label 3b-2slot --users 1 2 4 --target gateway --csv benchmarks/results.csv

Metrics per run:
  TTFT          time until the first token arrives (includes waiting in the queue)
  per-user t/s  tokens / (end - first token), averaged over users that finished
  total t/s     all tokens from all users / wall-clock time of the whole run
  errors        non-200 responses (e.g. 429 busy) or broken streams
"""
import argparse
import asyncio
import csv
import json
import os
import statistics
import time
from datetime import datetime

import httpx

PROMPT = "Explain how a transformer neural network works, step by step."


async def one_user(client, args, idx):
    t0 = time.perf_counter()
    first, n = None, 0
    if args.target == "llama":
        url = f"{args.llama_url}/v1/chat/completions"
        body = {"messages": [{"role": "user", "content": args.prompt}], "max_tokens": args.max_tokens,
                "temperature": args.temperature, "stream": True}
        headers = {}
    else:
        url = f"{args.gateway_url}/chat"
        body = {"messages": [{"role": "user", "content": args.prompt}], "max_tokens": args.max_tokens,
                "temperature": args.temperature}
        headers = {"x-api-key": args.key, "x-session-id": f"bench-{idx}-{time.time_ns()}"}
    try:
        async with client.stream("POST", url, json=body, headers=headers) as r:
            if r.status_code != 200:
                return {"error": r.status_code}
            if args.target == "llama":
                async for line in r.aiter_lines():
                    if line.startswith("data:") and "[DONE]" not in line:
                        try:
                            choices = json.loads(line[5:]).get("choices") or []
                        except json.JSONDecodeError:
                            continue
                        if choices and (choices[0].get("delta") or {}).get("content"):
                            first = first if first is not None else time.perf_counter() - t0
                            n += 1
            else:
                async for chunk in r.aiter_text():
                    if chunk:
                        first = first if first is not None else time.perf_counter() - t0
                        n += 1
    except httpx.HTTPError as exc:
        return {"error": repr(exc)}
    total = time.perf_counter() - t0
    rate = n / (total - first) if first is not None and total > first else 0.0
    return {"ttft": first, "tokens": n, "rate": rate, "total": total}


async def run(args, users):
    async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=10)) as client:
        t0 = time.perf_counter()
        res = await asyncio.gather(*[one_user(client, args, i) for i in range(users)])
        wall = time.perf_counter() - t0
    ok = [r for r in res if "error" not in r and r["tokens"] > 0]
    errors = len(res) - len(ok)
    if not ok:
        return {"users": users, "errors": errors}
    ttfts = sorted(r["ttft"] for r in ok)
    return {
        "users": users,
        "ttft_avg": statistics.mean(ttfts),
        "ttft_max": ttfts[-1],
        "per_user_tps": statistics.mean(r["rate"] for r in ok),
        "total_tps": sum(r["tokens"] for r in ok) / wall,
        "wall_s": wall,
        "errors": errors,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="name of this configuration, e.g. 3b-2slot")
    ap.add_argument("--users", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--target", choices=["llama", "gateway"], default="llama")
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--temperature", type=float, default=0.0, help="0 = repeatable output")
    ap.add_argument("--prompt", default=PROMPT)
    ap.add_argument("--llama-url", default=os.getenv("LLAMA_URL", "http://127.0.0.1:8080"))
    ap.add_argument("--gateway-url", default=os.getenv("GATEWAY_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--key", default=os.getenv("GATEWAY_KEY", "change-me"))
    ap.add_argument("--csv", help="append results to this CSV file")
    ap.add_argument("--no-warmup", action="store_true")
    args = ap.parse_args()

    print(f"== {args.label} | target={args.target} | max_tokens={args.max_tokens} ==")
    if not args.no_warmup:
        asyncio.run(run(args, 1))  # first request loads caches; do not measure it
    rows = []
    for u in args.users:
        row = asyncio.run(run(args, u))
        rows.append(row)
        if "ttft_avg" in row:
            print(f"{u:>2} users | TTFT avg {row['ttft_avg']:.2f}s max {row['ttft_max']:.2f}s | "
                  f"per-user {row['per_user_tps']:.1f} tok/s | total {row['total_tps']:.1f} tok/s | errors {row['errors']}")
        else:
            print(f"{u:>2} users | all requests failed ({row['errors']} errors)")
    if args.csv:
        new = not os.path.exists(args.csv)
        with open(args.csv, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "label", "target", "users", "ttft_avg_s", "ttft_max_s",
                            "per_user_tps", "total_tps", "wall_s", "errors"])
            for r in rows:
                w.writerow([datetime.now().isoformat(timespec="seconds"), args.label, args.target, r["users"],
                            *(round(r.get(k, 0), 3) for k in ("ttft_avg", "ttft_max", "per_user_tps", "total_tps", "wall_s")),
                            r["errors"]])
        print(f"appended to {args.csv}")


if __name__ == "__main__":
    main()
