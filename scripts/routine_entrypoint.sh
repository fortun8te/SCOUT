#!/usr/bin/env bash
# SCOUT Routine entrypoint — runs the monitor and nothing else.
# Explicitly suppresses any downstream git operations.
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_TERMINAL_PROMPT=0

# Source .env if present so env vars are available to the monitor
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

exec python src/monitor.py
