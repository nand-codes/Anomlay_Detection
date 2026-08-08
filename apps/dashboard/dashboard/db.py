from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import Settings

logger = logging.getLogger(__name__)

_EMPTY_OVERVIEW = {
    "total_rows": 0,
    "site_count": 0,
    "metric_count": 0,
    "first_ts": None,
    "last_ts": None,
}


class TimescaleRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url

    def _query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        try:
            with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params or ())
                    return list(cur.fetchall())
        except Exception as exc:
            logger.warning("TimescaleDB query failed: %s", exc)
            return []

    def overview(self) -> dict[str, Any]:
        rows = self._query(
            """
            SELECT
                count(*)::bigint AS total_rows,
                count(DISTINCT site) AS site_count,
                count(DISTINCT metric) AS metric_count,
                min(ts) AS first_ts,
                max(ts) AS last_ts
            FROM kpi_site_samples
            """
        )
        if not rows:
            return dict(_EMPTY_OVERVIEW)
        summary = dict(rows[0])
        for key in ("first_ts", "last_ts"):
            value = summary.get(key)
            if isinstance(value, datetime):
                summary[key] = value.isoformat()
        summary["total_rows"] = int(summary.get("total_rows") or 0)
        summary["site_count"] = int(summary.get("site_count") or 0)
        summary["metric_count"] = int(summary.get("metric_count") or 0)
        return summary

    def stats_by_site_metric(self) -> list[dict[str, Any]]:
        rows = self._query(
            """
            SELECT
                site,
                metric,
                count(*)::bigint AS row_count,
                round(avg(value)::numeric, 4) AS avg_value,
                round(min(value)::numeric, 4) AS min_value,
                round(max(value)::numeric, 4) AS max_value,
                max(ts) AS last_ts
            FROM kpi_site_samples
            GROUP BY site, metric
            ORDER BY site, metric
            """
        )
        for row in rows:
            if isinstance(row.get("last_ts"), datetime):
                row["last_ts"] = row["last_ts"].isoformat()
            if row.get("avg_value") is not None:
                row["avg_value"] = float(row["avg_value"])
        return rows

    def latest_samples(self, limit: int = 30) -> list[dict[str, Any]]:
        rows = self._query(
            """
            SELECT ts, site, metric, value
            FROM kpi_site_samples
            ORDER BY ts DESC, site, metric
            LIMIT %s
            """,
            (limit,),
        )
        for row in rows:
            if isinstance(row.get("ts"), datetime):
                row["ts"] = row["ts"].isoformat()
        return rows

    def timeseries(self, site: str, metric: str, limit: int = 96) -> list[dict[str, Any]]:
        rows = self._query(
            """
            SELECT ts, value
            FROM kpi_site_samples
            WHERE site = %s AND metric = %s
            ORDER BY ts DESC
            LIMIT %s
            """,
            (site, metric, limit),
        )
        rows.reverse()
        for row in rows:
            if isinstance(row.get("ts"), datetime):
                row["ts"] = row["ts"].isoformat()
        return rows

    def forecast_timeseries(self, site: str, metric: str) -> list[dict[str, Any]]:
        rows = self._query(
            """
            SELECT f.forecast_ts, f.predicted_value, f.lower_bound, f.upper_bound,
                   f.model_version, f.generated_at
            FROM forecasts f
            INNER JOIN (
                SELECT site, metric, max(generated_at) AS generated_at
                FROM forecasts
                WHERE site = %s AND metric = %s
                GROUP BY site, metric
            ) latest
              ON f.site = latest.site
             AND f.metric = latest.metric
             AND f.generated_at = latest.generated_at
            WHERE f.site = %s AND f.metric = %s
            ORDER BY f.forecast_ts ASC
            """,
            (site, metric, site, metric),
        )
        for row in rows:
            for key in ("forecast_ts", "generated_at"):
                if isinstance(row.get(key), datetime):
                    row[key] = row[key].isoformat()
            for key in ("predicted_value", "lower_bound", "upper_bound"):
                if row.get(key) is not None:
                    row[key] = float(row[key])
        return rows

    def forecast_overview(self) -> dict[str, Any]:
        rows = self._query(
            """
            SELECT
                count(*)::bigint AS total_rows,
                count(DISTINCT site || '/' || metric) AS series_count,
                max(generated_at) AS last_run
            FROM forecasts
            """
        )
        summary = rows[0] if rows else {}
        last_run = summary.get("last_run")
        if isinstance(last_run, datetime):
            summary["last_run"] = last_run.isoformat()
        summary["total_rows"] = int(summary.get("total_rows") or 0)
        summary["series_count"] = int(summary.get("series_count") or 0)
        return summary
