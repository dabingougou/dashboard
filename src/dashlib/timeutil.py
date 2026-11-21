"""Time helpers. Every time shown on a dashboard goes through format_time so
it is displayed in the configured timezone."""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_datetime(value: datetime | str) -> datetime:
    """Accept an aware/naive datetime or an ISO 8601 string. Naive = UTC."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def format_time(value: datetime | str, tz: tzinfo, style: str = "datetime") -> str:
    """Format a time in the dashboard timezone.

    style: "datetime" -> "Fri Nov 20, 21:05 PST"
           "date"     -> "Fri Nov 20"
           "time"     -> "21:05"
    """
    dt = to_datetime(value).astimezone(tz)
    date = f"{dt:%a %b} {dt.day}"
    if style == "date":
        return date
    if style == "time":
        return f"{dt:%H:%M}"
    return f"{date}, {dt:%H:%M} {dt:%Z}".rstrip()
