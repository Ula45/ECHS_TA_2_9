#!/usr/bin/env bash
# Start the FastAPI gateway. Use GATEWAY_HOST=0.0.0.0 only for LAN testing.
set -euo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
VENV_DIR="${VENV_DIR:-$HOME/ECHS_PRAC2/venv}"
cd "$ROOT_DIR"
exec "$VENV_DIR/bin/python" -m uvicorn gateway.main:app --host "${GATEWAY_HOST:-127.0.0.1}" --port 8000
