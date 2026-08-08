from __future__ import annotations

import json
import logging
from typing import Any

from confluent_kafka import KafkaException, Producer

from .config import Settings
from .generator import KpiMessage
from .metrics import MESSAGES_PUBLISHED, PUBLISH_ERRORS

logger = logging.getLogger(__name__)


class KpiPublisher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._producer = Producer(
            {
                "bootstrap.servers": settings.kafka_bootstrap,
                "client.id": "kpi-simulator",
                "acks": "1",
                "linger.ms": 5,
                "batch.size": 65536,
                "compression.type": "lz4",
            }
        )

    def _delivery_callback(self, err: Any, msg: Any) -> None:
        if err is not None:
            PUBLISH_ERRORS.inc()
            logger.error("Delivery failed for %s: %s", msg.key(), err)
            return
        MESSAGES_PUBLISHED.inc()

    def publish(self, message: KpiMessage) -> None:
        payload = json.dumps(message.to_dict()).encode("utf-8")
        key = f"{message.site}:{message.metric}".encode("utf-8")
        try:
            self._producer.produce(
                topic=self.settings.kpi_topic,
                key=key,
                value=payload,
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
        except KafkaException as exc:
            PUBLISH_ERRORS.inc()
            logger.error("Produce failed: %s", exc)
            raise

    def publish_batch(self, messages: list[KpiMessage]) -> None:
        for message in messages:
            self.publish(message)
        self.flush()

    def flush(self, timeout: float = 10.0) -> None:
        remaining = self._producer.flush(timeout)
        if remaining > 0:
            logger.warning("%s messages still in queue after flush", remaining)

    def close(self) -> None:
        self.flush()
