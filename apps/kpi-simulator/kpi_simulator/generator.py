from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import Settings
from .scheduler import format_ts


@dataclass
class KpiMessage:
    ts: str
    site: str
    metric: str
    value: float

    def to_dict(self) -> dict[str, str | float]:
        return {
            "ts": self.ts,
            "site": self.site,
            "metric": self.metric,
            "value": round(self.value, 4),
        }


@dataclass
class ActiveFault:
    site: str
    metric: str
    multiplier: float
    ends_at: float


@dataclass
class KpiGenerator:
    settings: Settings
    rng: random.Random = field(default_factory=random.Random)
    active_faults: dict[str, ActiveFault] = field(default_factory=dict)
    fault_started_this_tick: bool = False

    def __post_init__(self) -> None:
        self.rng.seed(42)

    def _baseline(self, site: str, metric: str) -> float:
        seed = hash(site) % 10000 + hash(metric) % 1000
        local = random.Random(seed)
        baselines = {
            "latency_ms": local.uniform(15.0, 85.0),
            "packet_loss_pct": local.uniform(0.01, 0.15),
            "cpu_pct": local.uniform(20.0, 65.0),
            "interface_util_pct": local.uniform(10.0, 75.0),
            "error_rate": local.uniform(0.0, 3.0),
        }
        return baselines[metric]

    def _diurnal_factor(self, moment: datetime) -> float:
        hour = moment.hour + moment.minute / 60.0
        return 1.0 + 0.2 * math.sin((2.0 * math.pi * hour) / 24.0)

    def _noise(self, metric: str) -> float:
        scales = {
            "latency_ms": 3.0,
            "packet_loss_pct": 0.02,
            "cpu_pct": 4.0,
            "interface_util_pct": 5.0,
            "error_rate": 0.4,
        }
        return self.rng.gauss(0.0, scales[metric])

    def _maybe_start_fault(self, site: str, now_mono: float) -> None:
        if site in self.active_faults:
            return
        if self.rng.random() >= self.settings.fault_injection_rate:
            return

        multipliers = {
            "latency_ms": self.rng.uniform(5.0, 12.0),
            "packet_loss_pct": self.rng.uniform(15.0, 40.0),
            "cpu_pct": self.rng.uniform(1.8, 2.8),
            "interface_util_pct": self.rng.uniform(1.5, 2.2),
            "error_rate": self.rng.uniform(8.0, 20.0),
        }
        fault_metric = self.rng.choice(["latency_ms", "packet_loss_pct", "cpu_pct"])
        self.active_faults[site] = ActiveFault(
            site=site,
            metric=fault_metric,
            multiplier=multipliers[fault_metric],
            ends_at=now_mono + self.settings.fault_duration_sec,
        )
        self.fault_started_this_tick = True

    def _expire_faults(self, now_mono: float) -> None:
        expired = [site for site, fault in self.active_faults.items() if fault.ends_at <= now_mono]
        for site in expired:
            del self.active_faults[site]

    def _apply_fault(self, site: str, metric: str, value: float) -> float:
        fault = self.active_faults.get(site)
        if fault is None or fault.metric != metric:
            return value
        return value * fault.multiplier

    def _clamp(self, metric: str, value: float) -> float:
        limits = {
            "latency_ms": (1.0, 5000.0),
            "packet_loss_pct": (0.0, 100.0),
            "cpu_pct": (0.0, 100.0),
            "interface_util_pct": (0.0, 100.0),
            "error_rate": (0.0, 1000.0),
        }
        low, high = limits[metric]
        return max(low, min(high, value))

    def generate_bucket(
        self, bucket_ts: datetime, now_mono: float | None = None
    ) -> list[KpiMessage]:
        """Emit one KPI per (site, metric) for the aligned bucket timestamp."""
        clock = time.monotonic() if now_mono is None else now_mono
        self.fault_started_this_tick = False
        self._expire_faults(clock)

        if bucket_ts.tzinfo is None:
            bucket_ts = bucket_ts.replace(tzinfo=timezone.utc)

        ts_label = format_ts(bucket_ts)
        messages: list[KpiMessage] = []

        for site in self.settings.sites:
            self._maybe_start_fault(site, clock)
            for metric in self.settings.metrics:
                value = self._baseline(site, metric)
                value *= self._diurnal_factor(bucket_ts)
                value += self._noise(metric)
                value = self._apply_fault(site, metric, value)
                value = self._clamp(metric, value)
                messages.append(
                    KpiMessage(ts=ts_label, site=site, metric=metric, value=value)
                )

        return messages

    @property
    def active_fault_count(self) -> int:
        return len(self.active_faults)
