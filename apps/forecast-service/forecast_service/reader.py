from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from .config import Settings
from .models import HistoryPoint, SeriesKey

logger = logging.getLogger(__name__)


class TimescaleReader:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def list_series(self) -> list[SeriesKey]:
        keys: list[SeriesKey] = []
        for site in self._settings.sites:
            for metric in self._settings.metrics:
                keys.append(SeriesKey(site=site, metric=metric))
        return keys

    def load_history(self, key: SeriesKey) -> list[HistoryPoint]:
        sql = """
            SELECT ts, value
            FROM kpi_site_samples
            WHERE site = %s AND metric = %s
            ORDER BY ts ASC
            LIMIT %s
        """
        with psycopg.connect(self._settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (key.site, key.metric, self._settings.forecast_history_limit),
                )
                rows = cur.fetchall()

        points: list[HistoryPoint] = []
        for row in rows:
            ts = row["ts"]
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            points.append(HistoryPoint(ts=ts, value=float(row["value"])))
        return points

    def latest_bucket_ts(self) -> datetime | None:
        sql = "SELECT max(ts) AS last_ts FROM kpi_site_samples"
        with psycopg.connect(self._settings.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                row = cur.fetchone()
        if not row or row["last_ts"] is None:
            return None
        ts = row["last_ts"]
        if isinstance(ts, datetime) and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
