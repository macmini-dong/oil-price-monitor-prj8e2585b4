#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${OIL_DB_PATH:-$ROOT_DIR/data/oil_prices.db}"
BACKUP_DIR="${OIL_BACKUP_DIR:-$ROOT_DIR/data/backups}"

mkdir -p "$BACKUP_DIR"

if [[ ! -f "$DB_PATH" ]]; then
  echo "DB_NOT_FOUND $DB_PATH" >&2
  exit 1
fi

STAMP="$(date -u '+%Y%m%d-%H%M%S')"
DEST="$BACKUP_DIR/oil_prices-$STAMP.db"
sqlite3 "$DB_PATH" ".backup '$DEST'"
echo "$DEST"

