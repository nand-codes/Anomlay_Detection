from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone

from .config import load_settings
from .metrics import FORECAST_POINTS, FORECAST_RUNS, SERIES_FORECASTED, start_metrics_server
from .reader import TimescaleReader
from .scheduler import seconds_until_next_bucket
from .trainer import ForecastTrainer
from .writer import ForecastWriter

logger = logging.getLogger(__name__)
_shutdown = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _shutdown
    logger.info("Received signal %s, shutting down...", signum)
    _shutdown = True


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def run_forecast_cycle(
    reader: TimescaleReader,
    trainer: ForecastTrainer,
    writer: ForecastWriter,
) -> int:
    settings = reader._settings
    origin_ts = reader.latest_bucket_ts()
    if origin_ts is None:
        logger.warning("No KPI history found — skipping forecast cycle")
        FORECAST_RUNS.labels(status="skipped").inc()
        return 0

    generated_at = datetime.now(timezone.utc)
    total_points = 0
    series_count = 0

    for key in reader.list_series():
        history = reader.load_history(key)
        if not history:
            logger.warning("No history for %s/%s", key.site, key.metric)
            continue

        points, model_version = trainer.forecast_series(
            key, history, origin_ts=origin_ts
        )
        written = writer.write_series(
            key,
            points,
            model_version=model_version,
            generated_at=generated_at,
        )
        total_points += written
        series_count += 1
        logger.info(
            "Forecast %s/%s: %d points (%s)",
            key.site,
            key.metric,
            written,
            model_version,
        )

    FORECAST_RUNS.labels(status="ok").inc()
    FORECAST_POINTS.inc(total_points)
    SERIES_FORECASTED.set(series_count)
    logger.info(
        "Forecast cycle complete: %d series, %d points, origin=%s",
        series_count,
        total_points,
        origin_ts.isoformat(),
    )
    return total_points


def run() -> int:
    _configure_logging()
    settings = load_settings()
    reader = TimescaleReader(settings)
    trainer = ForecastTrainer(settings)
    writer = ForecastWriter(settings)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    start_metrics_server(settings.metrics_port)

    logger.info(
        "Starting forecast-service: horizon=%dh (%d steps), interval=%ds, model=%s",
        settings.forecast_horizon_hours,
        settings.horizon_steps,
        settings.interval_sec,
        settings.forecast_model,
    )

    if settings.run_once:
        run_forecast_cycle(reader, trainer, writer)
        writer.close()
        return 0

    # Run immediately on startup, then align to bucket boundaries.
    run_forecast_cycle(reader, trainer, writer)

    try:
        while not _shutdown:
            wait_sec = seconds_until_next_bucket(
                datetime.now(timezone.utc), settings.interval_sec
            )
            logger.info("Next forecast cycle in %.0fs", wait_sec)
            deadline = time.monotonic() + wait_sec
            while not _shutdown and time.monotonic() < deadline:
                time.sleep(min(1.0, deadline - time.monotonic()))
            if _shutdown:
                break
            run_forecast_cycle(reader, trainer, writer)
    finally:
        writer.close()
        logger.info("Forecast service stopped")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
