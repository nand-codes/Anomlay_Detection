from prometheus_client import Counter, Gauge, Histogram, start_http_server

MESSAGES_CONSUMED = Counter(
    "ingest_messages_consumed_total",
    "Kafka messages consumed from kpis.raw",
)
ROWS_WRITTEN = Counter(
    "ingest_rows_written_total",
    "Rows written to kpi_samples",
)
VALIDATION_ERRORS = Counter(
    "ingest_validation_errors_total",
    "Messages that failed schema validation",
)
WRITE_ERRORS = Counter(
    "ingest_write_errors_total",
    "Database write failures",
)
BATCH_SIZE = Gauge(
    "ingest_last_batch_size",
    "Size of the most recent successful batch",
)
BATCH_DURATION = Histogram(
    "ingest_batch_write_seconds",
    "Time to write a batch to TimescaleDB",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
