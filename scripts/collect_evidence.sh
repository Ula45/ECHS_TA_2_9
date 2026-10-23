#!/usr/bin/env bash
# Save text evidence of the running system into docs/evidence/ so it can be committed
# and linked from the README. Run it on the Jetson while the stack is running.
set -uo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
OUT="$ROOT_DIR/docs/evidence"; mkdir -p "$OUT"
"$ROOT_DIR/scripts/check_env.sh" > "$OUT/system_state.txt" 2>&1
{ echo "Health:"; curl -s http://127.0.0.1:8000/health; echo; echo "Stats:"; \
  curl -s -H "x-api-key: ${GATEWAY_KEY:-change-me}" http://127.0.0.1:8000/stats; echo; } > "$OUT/gateway_api.txt" 2>&1
{ echo "Sample request through the gateway:"; \
  curl -s -N -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" \
    -H "x-api-key: ${GATEWAY_KEY:-change-me}" -H "x-session-id: evidence" \
    -d '{"messages":[{"role":"user","content":"In two sentences, what is edge AI?"}],"max_tokens":80}'; echo; } > "$OUT/sample_chat.txt" 2>&1
echo "Taking 10 tegrastats samples (needs sudo)..."
sudo timeout 11 tegrastats --interval 1000 > "$OUT/tegrastats_sample.txt" 2>&1 || true
echo "Saved to $OUT:"; ls -1 "$OUT"
