from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


def minutes_to_human(minutes: int | float | None) -> str | None:
    """Convert minutes to a human-readable string like '6 h 0 m'.

    Returns None for None or negative values.
    """
    if minutes is None:
        return None

    # robust: float -> int, other types -> None
    if isinstance(minutes, float):
        minutes = int(minutes)
    elif not isinstance(minutes, int):
        return None

    if minutes < 0:
        return None

    h = minutes // 60
    m = minutes % 60

    parts: list[str] = []
    if h:
        parts.append(f"{h} h")
    parts.append(f"{m} m")
    return " ".join(parts)


def get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Return attribute from object or key from dict (HA-friendly robustness)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse ISO datetime string into timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = dt_util.parse_datetime(value)
    if dt is None:
        return None
    return dt_util.as_utc(dt) if dt.tzinfo is None else dt
