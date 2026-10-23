#!/usr/bin/env bash
# Download and install cloudflared for ARM64, checking each step.
# (A plain "wget https://github.com" only saves GitHub's homepage, not the package.)
set -euo pipefail
ARCH="$(dpkg --print-architecture)"
[ "$ARCH" = "arm64" ] || { echo "Expected arm64, got $ARCH" >&2; exit 1; }
cd /tmp
wget -O cloudflared-linux-arm64.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
ls -lh cloudflared-linux-arm64.deb
file cloudflared-linux-arm64.deb | grep -q "Debian binary package" \
  || { echo "Download is not a .deb package (probably an HTML error page)." >&2; exit 1; }
sudo dpkg -i cloudflared-linux-arm64.deb
cloudflared --version
