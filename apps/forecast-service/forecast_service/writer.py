from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg

from .config import Settings
from .models import ForecastPoint, SeriesKey

logger = logging.getLogger(__name__)

INSERT_SQL = """
    INSERT INTO forecasts (
        forecast_ts, generated_at, site, metric,
        predicted_value, lower_bound, upper_bound,
        horizon_minutes, model_version
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

DELETE_SQL = """
    DELETE FROM forecasts
    WHERE site = %s AND metric = %s
"""


class ForecastWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._conn = psycopg.connect(settings.database_url, autocommit=False)

    def write_series(
        self,
        key: SeriesKey,
        points: list[ForecastPoint],
        *,
        model_version: str,
        generated_at: datetime | None = None,
    ) -> int:
        if not points:
            return 0

        generated = generated_at or datetime.now(timezone.utc)
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)

        rows = [
            (
                point.forecast_ts,
                generated,
                key.site,
                key.metric,
                point.predicted_value,
                point.lower_bound,
                point.upper_bound,
                self._settings.horizon_minutes,
                model_version,
            )
            for point in points
        ]

        with self._conn.cursor() as cur:
            cur.execute(DELETE_SQL, (key.site, key.metric))
            cur.executemany(INSERT_SQL, rows)
        self._conn.commit()
        return len(rows)

    def count_forecasts(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute("SELECT count(*)::bigint FROM forecasts")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def close(self) -> None:
        self._conn.close()
