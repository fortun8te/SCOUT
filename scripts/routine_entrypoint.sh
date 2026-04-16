#!/usr/bin/env bash
# SCOUT Routine entrypoint — runs the monitor and nothing else.
# Explicitly suppresses any downstream git operations.
set -euo pipefail
cd "$(dirname "$0")/.."
export GIT_TERMINAL_PROMPT=0
exec python src/monitor.py
