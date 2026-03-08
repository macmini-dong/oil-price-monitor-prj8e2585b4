#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/oil-monitor/app"
REPO_URL="https://github.com/macmini-dong/oil-price-monitor-prj8e2585b4.git"
HOST_PORT="${HOST_PORT:-18080}"

if [ ! -d "$APP_DIR/.git" ]; then
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

git fetch origin main
git reset --hard origin/main
HOST_PORT="$HOST_PORT" docker compose up -d --build

