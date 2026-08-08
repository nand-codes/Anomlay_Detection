from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from .config import Settings
from .metrics import MESSAGES_CONSUMED, VALIDATION_ERRORS
from .models import KpiRecord

logger = logging.getLogger(__name__)


class KpiConsumer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._consumer = Consumer(
            {
                "bootstrap.servers": settings.kafka_bootstrap,
                "group.id": settings.consumer_group,
                "auto.offset.reset": settings.auto_offset_reset,
                "enable.auto.commit": False,
                "session.timeout.ms": 10000,
            }
        )
        self._consumer.subscribe([settings.kpi_topic])

    def poll(self) -> Message | None:
        message = self._consumer.poll(self.settings.poll_timeout_sec)
        if message is None:
            return None
        if message.error():
            if message.error().code() == KafkaError._PARTITION_EOF:
                return None
            raise KafkaException(message.error())
        return message

    def parse_message(self, message: Message) -> KpiRecord | None:
        MESSAGES_CONSUMED.inc()
        try:
            payload: dict[str, Any] = json.loads(message.value().decode("utf-8"))
            return KpiRecord.model_validate(payload)
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            VALIDATION_ERRORS.inc()
            logger.warning("Invalid KPI message at %s:%s: %s", message.topic(), message.offset(), exc)
            return None

    def commit(self, message: Message) -> None:
        self._consumer.commit(message=message, asynchronous=False)

    def close(self) -> None:
        self._consumer.close()
