from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
from io import StringIO
import logging
from pathlib import Path
import threading
import time
from typing import Any, Optional
from urllib.request import Request, urlopen

from .database import OilDatabase, OilPricePoint, utc_now
from .settings import Settings


logger = logging.getLogger(__name__)

SYMBOL_MARKET_MAP = {
    "CL=F": "WTI Crude",
    "BZ=F": "Brent Crude",
}

FRED_SERIES_MAP = {
    "CL=F": "DCOILWTICO",
    "BZ=F": "DCOILBRENTEU",
}


@dataclass
class CollectorSnapshot:
    last_attempt_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_error: Optional[str] = None


class OilCollectorService:
    def __init__(self, db: OilDatabase, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._snapshot = CollectorSnapshot()
        self._snapshot_lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_forever, name="oil-collector", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def snapshot(self) -> CollectorSnapshot:
        with self._snapshot_lock:
            return CollectorSnapshot(
                last_attempt_at=self._snapshot.last_attempt_at,
                last_success_at=self._snapshot.last_success_at,
                last_error=self._snapshot.last_error,
            )

    def collect_once(self, trigger: str) -> dict[str, Any]:
        attempt_at = utc_now()
        self._set_snapshot(last_attempt_at=attempt_at.isoformat())
        try:
            points = self._fetch_quotes()
            inserted = self._db.insert_prices(points)
            self._set_snapshot(last_success_at=attempt_at.isoformat(), last_error=None)
            logger.info("Collect success trigger=%s inserted=%s", trigger, inserted)
            return {"ok": True, "inserted": inserted, "trigger": trigger}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Collect failed trigger=%s error=%s", trigger, exc)
            self._set_snapshot(last_error=str(exc))
            return {"ok": False, "error": str(exc), "trigger": trigger}

    def maybe_backup_daily(self) -> Optional[Path]:
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        done_date = self._db.get_meta("last_backup_utc_date")
        if done_date == today_utc:
            return None
        backup_file = self._db.create_backup()
        self._db.set_meta("last_backup_utc_date", today_utc)
        logger.info("Backup created %s", backup_file)
        return backup_file

    def _run_forever(self) -> None:
        self.collect_once(trigger="startup")
        self.maybe_backup_daily()
        while not self._stop_event.is_set():
            wait_seconds = self._seconds_until_next_run(interval_seconds=self._settings.fetch_interval_seconds)
            if self._stop_event.wait(wait_seconds):
                break
            self.collect_once(trigger="scheduled")
            self.maybe_backup_daily()

    def _fetch_quotes(self) -> list[OilPricePoint]:
        points: list[OilPricePoint] = []
        for symbol, market_name in SYMBOL_MARKET_MAP.items():
            series_id = FRED_SERIES_MAP[symbol]
            rows = self._fetch_fred_recent_points(series_id=series_id, max_points=240)
            for captured_at, price in rows:
                points.append(
                    OilPricePoint(
                        symbol=symbol,
                        market_name=market_name,
                        price=price,
                        currency="USD",
                        captured_at=captured_at,
                        source=f"FRED:{series_id}",
                    )
                )

        if not points:
            raise RuntimeError("No crude oil quote data returned from upstream provider.")
        return points

    def _fetch_fred_recent_points(self, series_id: str, max_points: int) -> list[tuple[datetime, float]]:
        url = self._settings.fred_csv_url_template.format(series_id=series_id)
        request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (OilMonitorBot/1.0)"},
        )
        with urlopen(request, timeout=self._settings.request_timeout_seconds) as response:  # noqa: S310
            csv_text = response.read().decode("utf-8")

        reader = csv.reader(StringIO(csv_text))
        _ = next(reader, None)  # header
        rows: list[tuple[datetime, float]] = []
        for row in reader:
            if len(row) < 2:
                continue
            raw_date = row[0].strip()
            raw_value = row[1].strip()
            if not raw_date or not raw_value or raw_value == ".":
                continue
            try:
                value = float(raw_value)
            except ValueError:
                continue
            captured_at = datetime.strptime(raw_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            rows.append((captured_at, value))

        if not rows:
            raise RuntimeError(f"No valid value found for FRED series {series_id}")

        return rows[-max_points:]

    def _set_snapshot(
        self,
        last_attempt_at: Optional[str] = None,
        last_success_at: Optional[str] = None,
        last_error: Optional[str] = None,
    ) -> None:
        with self._snapshot_lock:
            if last_attempt_at is not None:
                self._snapshot.last_attempt_at = last_attempt_at
            if last_success_at is not None:
                self._snapshot.last_success_at = last_success_at
            self._snapshot.last_error = last_error

    @staticmethod
    def _seconds_until_next_run(interval_seconds: int) -> float:
        now = time.time()
        next_ts = (int(now) // interval_seconds + 1) * interval_seconds
        wait = next_ts - now
        return wait if wait > 0 else float(interval_seconds)
