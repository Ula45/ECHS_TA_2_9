#!/usr/bin/env bash
# Create (or reuse) the virtualenv and install requirements with patient network settings,
# because PyPI can be very slow from the Jetson.
set -euo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
VENV_DIR="${VENV_DIR:-$HOME/ECHS_PRAC2/venv}"
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt" --default-timeout=300 --retries=10
"$VENV_DIR/bin/python" -c "import fastapi, uvicorn, httpx, requests, streamlit; print('All packages import correctly')"
