from __future__ import annotations

import logging
from typing import Sequence

import psycopg
from psycopg.rows import tuple_row

from .config import Settings
from .metrics import BATCH_DURATION, BATCH_SIZE, ROWS_WRITTEN, WRITE_ERRORS
from .models import KpiRecord

logger = logging.getLogger(__name__)

INSERT_SQL = (
    "INSERT INTO kpi_site_samples (ts, site, metric, value) "
    "VALUES (%s, %s, %s, %s) "
    "ON CONFLICT (ts, site, metric) DO UPDATE SET value = EXCLUDED.value"
)


class TimescaleWriter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._conn = psycopg.connect(settings.database_url, autocommit=False)

    def write_batch(self, records: Sequence[KpiRecord]) -> int:
        if not records:
            return 0

        rows = [record.as_row() for record in records]
        with BATCH_DURATION.time():
            try:
                with self._conn.cursor() as cur:
                    cur.executemany(INSERT_SQL, rows)
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                WRITE_ERRORS.inc()
                raise

        count = len(rows)
        ROWS_WRITTEN.inc(count)
        BATCH_SIZE.set(count)
        return count

    def verify_connection(self) -> None:
        with self._conn.cursor(row_factory=tuple_row) as cur:
            cur.execute("SELECT 1")
            cur.fetchone()

    def count_samples(self) -> int:
        with self._conn.cursor(row_factory=tuple_row) as cur:
            cur.execute("SELECT count(*)::bigint FROM kpi_site_samples")
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def close(self) -> None:
        self._conn.close()
