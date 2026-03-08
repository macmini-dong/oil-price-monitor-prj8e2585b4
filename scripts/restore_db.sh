#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup-file>" >&2
  exit 1
fi

BACKUP_FILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${OIL_DB_PATH:-$ROOT_DIR/data/oil_prices.db}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "BACKUP_NOT_FOUND $BACKUP_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"
TMP_DB="$DB_PATH.restore.tmp"

cp "$BACKUP_FILE" "$TMP_DB"
sqlite3 "$TMP_DB" "PRAGMA integrity_check;" | grep -q "^ok$"
mv "$TMP_DB" "$DB_PATH"

echo "RESTORE_OK $DB_PATH"

