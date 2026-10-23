#!/usr/bin/env bash
# Start the Streamlit chat UI on port 8501.
set -euo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
VENV_DIR="${VENV_DIR:-$HOME/ECHS_PRAC2/venv}"
cd "$ROOT_DIR"
exec "$VENV_DIR/bin/python" -m streamlit run frontend/app.py \
  --server.port 8501 --server.address "${FRONTEND_HOST:-0.0.0.0}" --server.headless true
