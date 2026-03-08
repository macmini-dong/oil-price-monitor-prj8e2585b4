from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class Settings:
    app_name: str
    db_path: Path
    backup_dir: Path
    fetch_interval_seconds: int
    request_timeout_seconds: float
    fred_csv_url_template: str
    admin_token: str
    app_version: str
    app_updated_at: str


def load_settings() -> Settings:
    db_path = Path(os.getenv("OIL_DB_PATH", str(DATA_DIR / "oil_prices.db"))).expanduser()
    backup_dir = Path(os.getenv("OIL_BACKUP_DIR", str(DATA_DIR / "backups"))).expanduser()

    try:
        interval = int(os.getenv("FETCH_INTERVAL_SECONDS", "600"))
    except ValueError:
        interval = 600
    if interval < 60:
        interval = 60

    try:
        timeout = float(os.getenv("FETCH_TIMEOUT_SECONDS", "8"))
    except ValueError:
        timeout = 8.0
    if timeout < 1:
        timeout = 1.0

    return Settings(
        app_name="International Crude Oil Trend Monitor",
        db_path=db_path,
        backup_dir=backup_dir,
        fetch_interval_seconds=interval,
        request_timeout_seconds=timeout,
        fred_csv_url_template=os.getenv(
            "OIL_FRED_CSV_URL_TEMPLATE",
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
        ),
        admin_token=os.getenv("OIL_ADMIN_TOKEN", "").strip(),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        app_updated_at=os.getenv("APP_UPDATED_AT", "2026-03-08 06:21 CST"),
    )
