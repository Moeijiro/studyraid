"""Time helpers.

Services never call datetime.now() themselves: routes pass `now` in. That keeps
the progression rules deterministic under test and lets the demo seeder replay
60 days of history through the same code paths as a live request.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def is_valid_timezone(name: str) -> bool:
    return name in available_timezones()


def local_date(dt: datetime, tz: str) -> date:
    """The calendar day an instant falls on for a user — what streaks are counted in."""
    return as_utc(dt).astimezone(zone(tz)).date()


def local_hour(dt: datetime, tz: str) -> int:
    return as_utc(dt).astimezone(zone(tz)).hour


def local_midnight_utc(day: date, tz: str) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=zone(tz)).astimezone(UTC)


def week_start(day: date) -> date:
    """Weeks start on Monday (ISO)."""
    return day - timedelta(days=day.weekday())
