#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/oil-monitor/app"
PERSIST_DATA_DIR="/opt/oil-monitor/data"
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

mkdir -p "$PERSIST_DATA_DIR"
if [ -L "$APP_DIR/data" ]; then
  rm -f "$APP_DIR/data"
fi
HOST_PORT="$HOST_PORT" OIL_DATA_DIR="$PERSIST_DATA_DIR" docker compose up -d --build
