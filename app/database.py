from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
from typing import Iterable, Optional


UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(UTC_FORMAT)


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, UTC_FORMAT).replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class OilPricePoint:
    symbol: str
    market_name: str
    price: float
    currency: str
    captured_at: datetime
    source: str


class OilDatabase:
    def __init__(self, db_path: Path, backup_dir: Path) -> None:
        self._db_path = db_path
        self._backup_dir = backup_dir
        self._lock = threading.Lock()

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS oil_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_oil_prices_symbol_time
                ON oil_prices(symbol, captured_at DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_oil_prices_unique_capture
                ON oil_prices(symbol, captured_at, source);

                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def insert_prices(self, points: Iterable[OilPricePoint]) -> int:
        payload = [
            (
                item.symbol,
                item.market_name,
                float(item.price),
                item.currency,
                utc_text(item.captured_at),
                item.source,
            )
            for item in points
        ]
        if not payload:
            return 0
        with self._lock:
            with self._connect() as conn:
                before_changes = conn.total_changes
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO oil_prices(symbol, market_name, price, currency, captured_at, source)
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
                inserted = conn.total_changes - before_changes
            return int(inserted)

    def list_points_since(self, since: datetime) -> list[OilPricePoint]:
        since_text = utc_text(since)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT symbol, market_name, price, currency, captured_at, source
                    FROM oil_prices
                    WHERE captured_at >= ?
                    ORDER BY captured_at ASC
                    """,
                    (since_text,),
                ).fetchall()
        return [self._row_to_point(row=row) for row in rows]

    def list_latest_points(self) -> list[OilPricePoint]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT p1.symbol, p1.market_name, p1.price, p1.currency, p1.captured_at, p1.source
                    FROM oil_prices p1
                    JOIN (
                        SELECT symbol, MAX(captured_at) AS captured_at
                        FROM oil_prices
                        GROUP BY symbol
                    ) p2
                    ON p1.symbol = p2.symbol AND p1.captured_at = p2.captured_at
                    ORDER BY p1.symbol ASC
                    """
                ).fetchall()
        return [self._row_to_point(row=row) for row in rows]

    def get_meta(self, key: str) -> Optional[str]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO meta(key, value)
                    VALUES(?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, value),
                )

    def create_backup(self) -> Path:
        timestamp = utc_now().strftime("%Y%m%d-%H%M%S")
        backup_file = self._backup_dir / f"oil_prices-{timestamp}.db"
        with self._lock:
            with self._connect() as src:
                with sqlite3.connect(backup_file) as dst:
                    src.backup(dst)
        return backup_file

    def list_backups(self) -> list[Path]:
        if not self._backup_dir.exists():
            return []
        return sorted((p for p in self._backup_dir.glob("oil_prices-*.db") if p.is_file()), reverse=True)

    def restore_from_backup(self, backup_file: Path) -> None:
        if not backup_file.exists() or not backup_file.is_file():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        with self._lock:
            with sqlite3.connect(backup_file) as src:
                with self._connect() as dst:
                    src.backup(dst)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_point(row: sqlite3.Row) -> OilPricePoint:
        return OilPricePoint(
            symbol=str(row["symbol"]),
            market_name=str(row["market_name"]),
            price=float(row["price"]),
            currency=str(row["currency"]),
            captured_at=parse_utc(str(row["captured_at"])),
            source=str(row["source"]),
        )
