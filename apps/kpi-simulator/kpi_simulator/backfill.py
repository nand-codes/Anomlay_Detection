from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timedelta, timezone

import psycopg

from .config import load_settings
from .generator import KpiGenerator, KpiMessage
from .scheduler import align_timestamp

logger = logging.getLogger(__name__)

INSERT_SQL = (
    "INSERT INTO kpi_site_samples (ts, site, metric, value) "
    "VALUES (%s, %s, %s, %s) "
    "ON CONFLICT (ts, site, metric) DO NOTHING"
)


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://netintel:netintel@localhost:5432/netintel",
    )


def iter_buckets(
    start: datetime, end: datetime, interval_sec: int
) -> list[datetime]:
    current = align_timestamp(start, interval_sec)
    end_aligned = align_timestamp(end, interval_sec)
    buckets: list[datetime] = []
    while current <= end_aligned:
        buckets.append(current)
        current = datetime.fromtimestamp(
            current.timestamp() + interval_sec, tz=timezone.utc
        )
    return buckets


def _message_rows(messages: list[KpiMessage]) -> list[tuple[datetime, str, str, float]]:
    rows: list[tuple[datetime, str, str, float]] = []
    for message in messages:
        ts = datetime.fromisoformat(message.ts.replace("Z", "+00:00"))
        rows.append((ts, message.site, message.metric, message.value))
    return rows


def generate_demo_rows(
    *,
    days: int,
    interval_sec: int,
    end: datetime | None = None,
) -> list[tuple[datetime, str, str, float]]:
    settings = load_settings()
    settings.interval_sec = interval_sec
    generator = KpiGenerator(settings=settings)

    if end is None:
        end = datetime.now(timezone.utc)
    end_aligned = align_timestamp(end, interval_sec)
    start = end_aligned - timedelta(days=days)

    buckets = iter_buckets(start, end_aligned, interval_sec)
    rows: list[tuple[datetime, str, str, float]] = []
    sim_mono = 0.0

    for bucket_ts in buckets:
        messages = generator.generate_bucket(bucket_ts, now_mono=sim_mono)
        rows.extend(_message_rows(messages))
        sim_mono += float(interval_sec)

    return rows


def write_rows(
    rows: list[tuple[datetime, str, str, float]],
    *,
    database_url: str,
    batch_size: int = 500,
) -> int:
    if not rows:
        return 0

    inserted = 0
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for offset in range(0, len(rows), batch_size):
                batch = rows[offset : offset + batch_size]
                cur.executemany(INSERT_SQL, batch)
                inserted += cur.rowcount
        conn.commit()
    return inserted


def run_backfill(
    *,
    days: int = 2,
    interval_sec: int | None = None,
    database_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, int | str]:
    settings = load_settings()
    interval = interval_sec or settings.interval_sec
    db_url = database_url or _database_url()

    rows = generate_demo_rows(days=days, interval_sec=interval)
    bucket_count = len(rows) // max(1, len(settings.sites) * len(settings.metrics))

    summary: dict[str, int | str] = {
        "days": days,
        "interval_sec": interval,
        "buckets": bucket_count,
        "rows_generated": len(rows),
        "rows_inserted": 0,
    }

    if dry_run:
        logger.info("Dry run: would insert %d rows (%d buckets)", len(rows), bucket_count)
        return summary

    inserted = write_rows(rows, database_url=db_url)
    summary["rows_inserted"] = inserted
    logger.info(
        "Backfill complete: %d rows inserted (%d generated, %d buckets, %d days)",
        inserted,
        len(rows),
        bucket_count,
        days,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed TimescaleDB with historical KPI demo data."
    )
    parser.add_argument("--days", type=int, default=2, help="Days of history to generate")
    parser.add_argument(
        "--interval-sec",
        type=int,
        default=None,
        help="Bucket interval (default: from config.yaml)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Postgres URL (default: DATABASE_URL env or localhost)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Generate only, no DB write")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    summary = run_backfill(
        days=args.days,
        interval_sec=args.interval_sec,
        database_url=args.database_url,
        dry_run=args.dry_run,
    )
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
