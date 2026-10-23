#!/usr/bin/env bash
# Start llama-server with a named profile.
#   ./scripts/start_llama_server.sh 3b-1slot
#
# -c is the TOTAL context, split across --parallel slots (e.g. 4096 / 2 slots = 2048 tokens each).
# Only 3b-1slot has been confirmed on the author's board. The rest are experiments:
# raise slots one step at a time and watch memory with tegrastats/jtop.
set -euo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/ECHS_PRAC2/llama.cpp}"
MODELS_DIR="${MODELS_DIR:-$HOME/ECHS_PRAC2/models}"
PORT="${LLAMA_PORT:-8080}"
M3B="Llama-3.2-3B-Instruct-Q4_K_M.gguf"
M8B="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
PROFILE="${1:-3b-1slot}"

case "$PROFILE" in
  3b-1slot) MODEL="$M3B"; CTX=2048; SLOTS=1 ;;   # confirmed working
  3b-2slot) MODEL="$M3B"; CTX=4096; SLOTS=2 ;;   # next experiment
  3b-4slot) MODEL="$M3B"; CTX=8192; SLOTS=4 ;;   # experimental, memory-hungry
  8b-1slot) MODEL="$M8B"; CTX=2048; SLOTS=1 ;;   # experimental, very tight on 8 GB
  8b-2slot) MODEL="$M8B"; CTX=4096; SLOTS=2 ;;   # experimental, likely too large
  *) echo "Unknown profile '$PROFILE'. Use: 3b-1slot 3b-2slot 3b-4slot 8b-1slot 8b-2slot" >&2; exit 1 ;;
esac

BIN="$LLAMA_CPP_DIR/build/bin/llama-server"
[ -x "$BIN" ] || { echo "llama-server not found at $BIN. Build llama.cpp first (see README)." >&2; exit 1; }
[ -f "$MODELS_DIR/$MODEL" ] || { echo "Model file not found: $MODELS_DIR/$MODEL" >&2; exit 1; }

echo "Profile: $PROFILE  model=$MODEL  total ctx=$CTX  slots=$SLOTS  ($((CTX / SLOTS)) tokens per slot)"
echo "Free memory before start:"; free -h | sed -n '1,2p'

# EXTRA_ARGS is intentionally unquoted so several flags can be passed, e.g. EXTRA_ARGS="--threads 6"
# shellcheck disable=SC2086
exec "$BIN" -m "$MODELS_DIR/$MODEL" \
  -ngl 99 -c "$CTX" --parallel "$SLOTS" --cont-batching -fa on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --host 127.0.0.1 --port "$PORT" --metrics ${EXTRA_ARGS:-}
