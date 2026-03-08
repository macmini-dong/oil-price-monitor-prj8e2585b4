#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/artifacts"
PID_FILE="$RUN_DIR/oil-monitor.pid"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-18080}"

mkdir -p "$RUN_DIR" "$LOG_DIR" "$ROOT_DIR/data/backups"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt" >/dev/null

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID"
    sleep 1
  fi
fi

nohup "$VENV_DIR/bin/uvicorn" app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  >"$LOG_DIR/server.log" 2>&1 &
NEW_PID="$!"
echo "$NEW_PID" > "$PID_FILE"

for _ in $(seq 1 25); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null; then
    echo "DEPLOY_OK http://127.0.0.1:${PORT}/"
    exit 0
  fi
  sleep 1
done

echo "DEPLOY_FAILED, see log: $LOG_DIR/server.log" >&2
exit 1

