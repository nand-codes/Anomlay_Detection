from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timezone

from .config import load_settings
from .generator import KpiGenerator
from .metrics import ACTIVE_FAULTS, FAULTS_INJECTED, PUBLISH_RATE, start_metrics_server
from .publisher import KpiPublisher
from .scheduler import align_timestamp, seconds_until_next_bucket

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


def _track_faults(generator: KpiGenerator) -> None:
    if generator.fault_started_this_tick:
        FAULTS_INJECTED.inc()
    ACTIVE_FAULTS.set(generator.active_fault_count)


def _resolve_bucket_ts(settings, now: datetime) -> datetime:
    if settings.align_to_boundary:
        return align_timestamp(now, settings.interval_sec)
    return now


def run() -> int:
    _configure_logging()
    settings = load_settings()
    generator = KpiGenerator(settings=settings)
    publisher = KpiPublisher(settings)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    start_metrics_server(settings.metrics_port)
    points_per_bucket = len(settings.sites) * len(settings.metrics)
    logger.info(
        "Starting KPI simulator: bootstrap=%s topic=%s interval_sec=%d align=%s "
        "sites=%d metrics=%d points_per_bucket=%d metrics_port=%d",
        settings.kafka_bootstrap,
        settings.kpi_topic,
        settings.interval_sec,
        settings.align_to_boundary,
        len(settings.sites),
        len(settings.metrics),
        points_per_bucket,
        settings.metrics_port,
    )

    try:
        while not _shutdown:
            now = datetime.now(timezone.utc)
            wait_sec = seconds_until_next_bucket(now, settings.interval_sec)
            if wait_sec > 0:
                logger.info("Next bucket in %.0fs (interval=%ds)", wait_sec, settings.interval_sec)
                slept = 0.0
                while slept < wait_sec and not _shutdown:
                    chunk = min(1.0, wait_sec - slept)
                    time.sleep(chunk)
                    slept += chunk

            if _shutdown:
                break

            bucket_ts = _resolve_bucket_ts(settings, datetime.now(timezone.utc))
            messages = generator.generate_bucket(bucket_ts)
            _track_faults(generator)
            publisher.publish_batch(messages)

            PUBLISH_RATE.set(len(messages) / settings.interval_sec)
            logger.info(
                "Published bucket %s: %d KPIs (%d sites x %d metrics) active_faults=%d",
                messages[0].ts if messages else bucket_ts.isoformat(),
                len(messages),
                len(settings.sites),
                len(settings.metrics),
                generator.active_fault_count,
            )
    finally:
        publisher.close()
        logger.info("Simulator stopped")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
