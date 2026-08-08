from __future__ import annotations

from prometheus_client import Counter, Gauge, start_http_server

FORECAST_RUNS = Counter("forecast_runs_total", "Forecast job executions", ["status"])
FORECAST_POINTS = Counter("forecast_points_total", "Forecast points written")
SERIES_FORECASTED = Gauge("forecast_series_count", "Series forecasted in last run")


def start_metrics_server(port: int) -> None:
    start_http_server(port)
