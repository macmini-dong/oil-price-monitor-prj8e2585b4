#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/run/oil-monitor.pid"
PORT="${PORT:-18080}"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "PROCESS_RUNNING pid=$PID"
  else
    echo "PROCESS_NOT_RUNNING"
  fi
else
  echo "PROCESS_UNKNOWN"
fi

if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null; then
  echo "HTTP_HEALTH_OK http://127.0.0.1:${PORT}/"
else
  echo "HTTP_HEALTH_FAILED http://127.0.0.1:${PORT}/"
fi

