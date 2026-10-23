#!/usr/bin/env bash
# Log GPU/CPU/memory/power/temperature once per second to logs/tegrastats_<label>.log.
#   ./scripts/monitor.sh 3b-2slot      (Ctrl+C to stop)
# Columns of interest: GR3D_FREQ = GPU load, RAM, SWAP, gpu@ / cpu@ temperatures, VDD_IN = board power.
set -euo pipefail
# shellcheck disable=SC1091
source "$(dirname "$0")/_env.sh"
LABEL="${1:-run}"
mkdir -p "$ROOT_DIR/logs"
OUT="$ROOT_DIR/logs/tegrastats_${LABEL}_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to $OUT  (Ctrl+C to stop)"
sudo tegrastats --interval 1000 --logfile "$OUT"
