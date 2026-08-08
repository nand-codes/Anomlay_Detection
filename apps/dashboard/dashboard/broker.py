from __future__ import annotations

import logging
from typing import Any

import httpx
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient

from .config import Settings

logger = logging.getLogger(__name__)


class BrokerRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap})

    def cluster_health(self) -> dict[str, Any]:
        base = self._settings.redpanda_admin_url.rstrip("/")
        for path in ("/v1/cluster/health_overview", "/v1/status/ready"):
            try:
                response = httpx.get(f"{base}{path}", timeout=5.0)
                response.raise_for_status()
                payload = response.json()
                if path.endswith("health_overview"):
                    return payload
                return {"healthy": payload.get("status") == "ready", **payload}
            except Exception as exc:
                logger.debug("Redpanda health probe failed for %s: %s", path, exc)
        return {"healthy": False, "error": "Unable to reach Redpanda admin API"}

    def topic_overview(self) -> dict[str, Any]:
        topic = self._settings.kpi_topic
        try:
            metadata = self._admin.list_topics(topic=topic, timeout=10)
        except Exception as exc:
            logger.warning("Failed to list Kafka topics: %s", exc)
            return {
                "topic": topic,
                "exists": False,
                "partitions": [],
                "total_messages": 0,
                "error": str(exc),
            }

        if topic not in metadata.topics:
            return {
                "topic": topic,
                "exists": False,
                "partitions": [],
                "total_messages": 0,
            }

        topic_meta = metadata.topics[topic]
        partitions: list[dict[str, Any]] = []
        total_messages = 0

        consumer = Consumer(
            {
                "bootstrap.servers": self._settings.kafka_bootstrap,
                "group.id": "netintel-dashboard-probe",
                "enable.auto.commit": False,
            }
        )
        try:
            for partition_id in sorted(topic_meta.partitions):
                tp = TopicPartition(topic, partition_id)
                try:
                    low, high = consumer.get_watermark_offsets(tp, timeout=10)
                except Exception as exc:
                    logger.warning("Offset lookup failed for partition %s: %s", partition_id, exc)
                    low, high = 0, 0
                count = max(0, high - low)
                total_messages += count
                partitions.append(
                    {
                        "partition": partition_id,
                        "low_offset": low,
                        "high_offset": high,
                        "message_count": count,
                    }
                )
        finally:
            consumer.close()

        return {
            "topic": topic,
            "exists": True,
            "partition_count": len(partitions),
            "total_messages": total_messages,
            "partitions": partitions,
        }

    def overview(self) -> dict[str, Any]:
        health = self.cluster_health()
        topic = self.topic_overview()
        is_healthy = bool(health.get("is_healthy") or health.get("healthy"))
        return {
            "bootstrap": self._settings.kafka_bootstrap,
            "admin_url": self._settings.redpanda_admin_url,
            "healthy": is_healthy,
            "health": health,
            "topic": topic,
        }
