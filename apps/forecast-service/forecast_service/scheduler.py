from __future__ import annotations

from datetime import datetime, timezone


def align_timestamp(moment: datetime, interval_sec: int) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    epoch = int(moment.timestamp())
    aligned = (epoch // interval_sec) * interval_sec
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def seconds_until_next_bucket(moment: datetime, interval_sec: int) -> float:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    epoch = int(moment.timestamp())
    next_bucket = ((epoch // interval_sec) + 1) * interval_sec
    return max(0.0, float(next_bucket - epoch))
