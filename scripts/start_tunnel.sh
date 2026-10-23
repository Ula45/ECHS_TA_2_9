#!/usr/bin/env bash
# Publish the Streamlit UI through a Cloudflare quick tunnel.
# Prints a https://<random>.trycloudflare.com URL that changes every restart.
set -euo pipefail
command -v cloudflared >/dev/null || { echo "cloudflared is not installed. Run scripts/install_cloudflared.sh" >&2; exit 1; }
exec cloudflared tunnel --url http://localhost:8501
