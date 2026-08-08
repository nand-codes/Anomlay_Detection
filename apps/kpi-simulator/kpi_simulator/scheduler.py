from __future__ import annotations

from datetime import datetime, timezone


def align_timestamp(moment: datetime, interval_sec: int) -> datetime:
    """Floor *moment* to the nearest interval boundary (UTC)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    epoch = int(moment.timestamp())
    aligned = (epoch // interval_sec) * interval_sec
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def seconds_until_next_bucket(moment: datetime, interval_sec: int) -> float:
    """Seconds until the next aligned bucket after *moment*."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    epoch = int(moment.timestamp())
    next_bucket = ((epoch // interval_sec) + 1) * interval_sec
    return max(0.0, float(next_bucket - epoch))


def format_ts(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")
