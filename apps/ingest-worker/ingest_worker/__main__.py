from __future__ import annotations

import logging
import signal
import sys
import time

from confluent_kafka import Message

from .config import load_settings
from .consumer import KpiConsumer
from .metrics import start_metrics_server
from .models import KpiRecord
from .writer import TimescaleWriter

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


def _flush_batch(
    consumer: KpiConsumer,
    writer: TimescaleWriter,
    batch: list[KpiRecord],
    last_message: Message | None,
) -> Message | None:
    if not batch:
        return last_message

    writer.write_batch(batch)
    if last_message is not None:
        consumer.commit(last_message)
    logger.debug("Wrote batch of %d rows", len(batch))
    return None


def run() -> int:
    _configure_logging()
    settings = load_settings()
    consumer = KpiConsumer(settings)
    writer = TimescaleWriter(settings)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    start_metrics_server(settings.metrics_port)
    writer.verify_connection()

    logger.info(
        "Starting ingest-worker: kafka=%s topic=%s group=%s db=%s batch_size=%d",
        settings.kafka_bootstrap,
        settings.kpi_topic,
        settings.consumer_group,
        settings.database_url.split("@")[-1],
        settings.batch_size,
    )

    batch: list[KpiRecord] = []
    last_message: Message | None = None
    batch_started = time.monotonic()
    rows_since_log = 0
    log_started = time.monotonic()

    try:
        while not _shutdown:
            message = consumer.poll()
            now = time.monotonic()

            if message is not None:
                record = consumer.parse_message(message)
                last_message = message
                if record is not None:
                    batch.append(record)

            should_flush = (
                len(batch) >= settings.batch_size
                or (batch and now - batch_started >= settings.batch_timeout_sec)
            )
            if should_flush:
                written = len(batch)
                last_message = _flush_batch(consumer, writer, batch, last_message)
                rows_since_log += written
                batch = []
                batch_started = now

            if now - log_started >= settings.log_interval_sec:
                total = writer.count_samples()
                logger.info(
                    "Ingested %d rows in %.1fs | kpi_samples total=%d",
                    rows_since_log,
                    now - log_started,
                    total,
                )
                rows_since_log = 0
                log_started = now

        if batch:
            _flush_batch(consumer, writer, batch, last_message)
    finally:
        consumer.close()
        writer.close()
        logger.info("Ingest worker stopped")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
