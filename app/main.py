from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import logging
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .collector import OilCollectorService, SYMBOL_MARKET_MAP
from .database import OilDatabase, OilPricePoint, utc_now
from .settings import PROJECT_ROOT, load_settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

SETTINGS = load_settings()
DB = OilDatabase(db_path=SETTINGS.db_path, backup_dir=SETTINGS.backup_dir)
COLLECTOR = OilCollectorService(db=DB, settings=SETTINGS)
STATIC_DIR = PROJECT_ROOT / "app" / "static"

app = FastAPI(title=SETTINGS.app_name, version=SETTINGS.app_version)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup() -> None:
    DB.initialize()
    COLLECTOR.start()
    logger.info("Oil monitor started db=%s interval=%s", SETTINGS.db_path, SETTINGS.fetch_interval_seconds)


@app.on_event("shutdown")
def on_shutdown() -> None:
    COLLECTOR.stop()
    logger.info("Oil monitor stopped.")


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not SETTINGS.admin_token:
        return
    if x_admin_token != SETTINGS.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized admin token")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "time": utc_now().isoformat()}


@app.get("/api/v1/prices")
def get_prices(hours: int = 72) -> dict[str, object]:
    if hours <= 0 or hours > 24 * 30:
        raise HTTPException(status_code=400, detail="hours must be within 1~720")

    since = utc_now() - timedelta(hours=hours)
    points = DB.list_points_since(since=since)
    grouped: dict[str, list[OilPricePoint]] = defaultdict(list)
    for point in points:
        grouped[point.symbol].append(point)

    series: list[dict[str, object]] = []
    for symbol, market_name in SYMBOL_MARKET_MAP.items():
        rows = grouped.get(symbol, [])
        series.append(
            {
                "symbol": symbol,
                "market_name": market_name,
                "points": [
                    {
                        "price": row.price,
                        "currency": row.currency,
                        "captured_at": row.captured_at.isoformat(),
                        "source": row.source,
                    }
                    for row in rows
                ],
            }
        )

    latest_points = DB.list_latest_points()
    latest = [
        {
            "symbol": row.symbol,
            "market_name": row.market_name,
            "price": row.price,
            "currency": row.currency,
            "captured_at": row.captured_at.isoformat(),
            "source": row.source,
        }
        for row in latest_points
    ]

    snapshot = COLLECTOR.snapshot()
    return {
        "generated_at": utc_now().isoformat(),
        "hours": hours,
        "series": series,
        "latest": latest,
        "collector": {
            "last_attempt_at": snapshot.last_attempt_at,
            "last_success_at": snapshot.last_success_at,
            "last_error": snapshot.last_error,
            "interval_seconds": SETTINGS.fetch_interval_seconds,
        },
        "app": {
            "name": SETTINGS.app_name,
            "version": SETTINGS.app_version,
            "updated_at": SETTINGS.app_updated_at,
        },
    }


@app.post("/api/v1/admin/collect")
def collect_now(_: None = Depends(require_admin_token)) -> dict[str, object]:
    return COLLECTOR.collect_once(trigger="manual-api")


@app.post("/api/v1/admin/backup")
def create_backup(_: None = Depends(require_admin_token)) -> dict[str, object]:
    backup_file = COLLECTOR.maybe_backup_daily()
    if backup_file is None:
        backup_file = DB.create_backup()
    return {"ok": True, "backup_file": str(backup_file)}


@app.get("/api/v1/backups")
def list_backups(_: None = Depends(require_admin_token)) -> dict[str, object]:
    backups = [str(path) for path in DB.list_backups()]
    return {"count": len(backups), "items": backups}
