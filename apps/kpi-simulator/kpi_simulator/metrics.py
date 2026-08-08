from prometheus_client import Counter, Gauge, start_http_server

MESSAGES_PUBLISHED = Counter(
    "kpi_messages_published_total",
    "Total KPI messages successfully delivered to Kafka",
)
PUBLISH_ERRORS = Counter(
    "kpi_publish_errors_total",
    "Total KPI publish/delivery errors",
)
FAULTS_INJECTED = Counter(
    "kpi_faults_injected_total",
    "Total fault injections started",
)
ACTIVE_FAULTS = Gauge(
    "kpi_active_faults",
    "Number of devices currently in a fault state",
)
PUBLISH_RATE = Gauge(
    "kpi_publish_rate_per_sec",
    "Recent publish rate (messages/sec)",
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
