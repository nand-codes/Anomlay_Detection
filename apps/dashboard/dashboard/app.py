from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .broker import BrokerRepository
from .config import load_settings
from .db import TimescaleRepository

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

settings = load_settings()
timescale = TimescaleRepository(settings)
broker = BrokerRepository(settings)

app = FastAPI(title="NetIntel Dashboard", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/overview")
def api_overview() -> dict:
    return {
        "timescale": timescale.overview(),
        "broker": broker.overview(),
    }


@app.get("/api/timescale/stats")
def api_timescale_stats() -> dict:
    return {"items": timescale.stats_by_site_metric()}


@app.get("/api/timescale/latest")
def api_timescale_latest(limit: int = Query(default=30, ge=1, le=200)) -> dict:
    return {"items": timescale.latest_samples(limit=limit)}


@app.get("/api/timescale/timeseries")
def api_timescale_timeseries(
    site: str = Query(default="siteA"),
    metric: str = Query(default="latency_ms"),
    limit: int = Query(default=96, ge=1, le=500),
) -> dict:
    return {
        "site": site,
        "metric": metric,
        "points": timescale.timeseries(site=site, metric=metric, limit=limit),
    }


@app.get("/api/broker/overview")
def api_broker_overview() -> dict:
    return broker.overview()


@app.get("/api/broker/topic")
def api_broker_topic() -> dict:
    return broker.topic_overview()


@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok"}
