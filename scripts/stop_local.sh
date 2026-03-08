#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/run/oil-monitor.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "NO_PID_FILE"
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  sleep 1
fi

rm -f "$PID_FILE"
echo "STOPPED"

