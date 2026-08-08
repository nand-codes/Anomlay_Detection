from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SeriesKey:
    site: str
    metric: str


@dataclass(frozen=True)
class HistoryPoint:
    ts: datetime
    value: float


@dataclass(frozen=True)
class ForecastPoint:
    forecast_ts: datetime
    predicted_value: float
    lower_bound: float | None
    upper_bound: float | None
