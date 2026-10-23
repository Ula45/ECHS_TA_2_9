#!/usr/bin/env bash
# Sourced by the other scripts. Loads .env from the project root when it exists.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi
export ROOT_DIR
