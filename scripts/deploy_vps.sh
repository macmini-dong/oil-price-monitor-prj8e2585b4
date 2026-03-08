#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VPS_HOST="${VPS_HOST:-43.167.189.158}"
VPS_USER="${VPS_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-/Users/macmini_dong/Desktop/openclaw.pem}"
REMOTE_BASE="${REMOTE_BASE:-/opt/oil-monitor}"
REMOTE_DIR="${REMOTE_DIR:-$REMOTE_BASE/app}"
HOST_PORT="${HOST_PORT:-18080}"

SSH_OPTS=(-i "$SSH_KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

echo "[1/5] Prepare remote directories..."
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" \
  "sudo mkdir -p '$REMOTE_DIR' '$REMOTE_BASE/data' && sudo chown -R ${VPS_USER}:${VPS_USER} '$REMOTE_BASE'"

echo "[2/5] Sync project files..."
rsync -az --delete \
  --exclude '.venv' \
  --exclude 'data' \
  --exclude 'artifacts' \
  --exclude 'run' \
  -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes" \
  "$ROOT_DIR/" "${VPS_USER}@${VPS_HOST}:$REMOTE_DIR/"

echo "[3/5] Build and launch containers..."
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" \
  "cd '$REMOTE_DIR' && HOST_PORT='$HOST_PORT' docker compose up -d --build"

echo "[4/5] Open firewall port if needed..."
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "sudo ufw allow ${HOST_PORT}/tcp >/dev/null || true"

echo "[5/5] Health check..."
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "curl -sS http://127.0.0.1:${HOST_PORT}/healthz"

echo
echo "DEPLOY_OK http://${VPS_HOST}:${HOST_PORT}/"

