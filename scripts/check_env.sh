#!/usr/bin/env bash
# Print the state of the board and the stack. Read-only. Safe to run any time.
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
echo "== System =="; uname -a; grep PRETTY_NAME /etc/os-release || true
echo; echo "== Memory / swap =="; free -h; swapon --show || true
echo; echo "== Disk =="; df -h / "$HOME" 2>/dev/null | sort -u
echo; echo "== Power mode / default boot target =="
sudo -n nvpmodel -q 2>/dev/null || echo "(run 'sudo nvpmodel -q' manually)"
systemctl get-default || true
echo; echo "== Project files =="
ls -lh "${MODELS_DIR:-$HOME/ECHS_PRAC2/models}" 2>/dev/null || echo "models dir not found"
ls -lh "${LLAMA_CPP_DIR:-$HOME/ECHS_PRAC2/llama.cpp}/build/bin/llama-server" 2>/dev/null || echo "llama-server not built"
echo; echo "== Running processes =="
pgrep -af "llama-server|uvicorn|streamlit|cloudflared" || echo "none of the stack is running"
echo; echo "== Listening ports (8000 gateway, 8080 llama, 8501 UI) =="
ss -lnt 2>/dev/null | grep -E ':(8000|8080|8501)\b' || echo "none"
echo; echo "== Health checks =="
curl -s --max-time 3 "http://127.0.0.1:${LLAMA_PORT:-8080}/health" || echo "llama-server: no answer"; echo
curl -s --max-time 3 "http://127.0.0.1:8000/health" || echo "gateway: no answer"; echo
echo; echo "== Python packages =="
"${VENV_DIR:-$HOME/ECHS_PRAC2/venv}/bin/python" -m pip list 2>/dev/null | grep -i -E "fastapi|uvicorn|httpx|requests|streamlit" || echo "packages not installed in venv"
