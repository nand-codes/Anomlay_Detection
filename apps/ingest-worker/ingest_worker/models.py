from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class KpiRecord(BaseModel):
    ts: datetime
    site: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float

    @field_validator("ts", mode="before")
    @classmethod
    def parse_ts(cls, value: Any) -> Any:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        raise ValueError(f"Unsupported timestamp: {value!r}")

    def as_row(self) -> tuple[datetime, str, str, float]:
        return (self.ts, self.site, self.metric, self.value)
