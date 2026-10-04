"""The city clock (D38, D50): real time, in the city's time zone.

Pure functions over datetimes; callers pass the current UTC time in.
"""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

CITY_TZ = ZoneInfo("America/New_York")
WEATHER_BLOCK_HOURS = 3

# Parts of the day, by the hour they start (city time).
PARTS_OF_DAY: tuple[tuple[int, str], ...] = (
    (0, "small hours"),
    (5, "dawn"),
    (7, "morning"),
    (11, "midday"),
    (14, "afternoon"),
    (17, "dusk"),
    (20, "evening"),
    (23, "night"),
)
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("times must be timezone-aware")
    return moment


def city_time(moment: datetime) -> datetime:
    """The same instant on the city's clock."""
    return _aware(moment).astimezone(CITY_TZ)


def part_of_day(moment: datetime) -> str:
    hour = city_time(moment).hour
    return next(name for start, name in reversed(PARTS_OF_DAY) if hour >= start)


def weekday(moment: datetime) -> str:
    return WEEKDAYS[city_time(moment).weekday()]


def city_day(moment: datetime) -> str:
    """The city date, as YYYY-MM-DD. The city's day turns over at city midnight."""
    return city_time(moment).date().isoformat()


def day_start_utc(moment: datetime) -> datetime:
    """The instant the current city day began, in UTC (handles daylight saving)."""
    local = city_time(moment)
    midnight = datetime.combine(local.date(), time(0), tzinfo=CITY_TZ)
    return midnight.astimezone(UTC)


def weather_block_start(moment: datetime) -> datetime:
    """The start of the 3-hour weather block this instant falls in, in UTC."""
    local = city_time(moment)
    hour = local.hour - local.hour % WEATHER_BLOCK_HOURS
    start = datetime.combine(local.date(), time(hour), tzinfo=CITY_TZ)
    return start.astimezone(UTC)


def minutes_into_day(moment: datetime) -> int:
    local = city_time(moment)
    return local.hour * 60 + local.minute


def describe(moment: datetime) -> str:
    """'Tuesday 9:40 pm, evening' on the city clock."""
    local = city_time(moment)
    clock = local.strftime("%I:%M %p").lstrip("0").lower()
    return f"{weekday(moment).title()} {clock}, {part_of_day(moment)}"


def describe_span(seconds: int) -> str:
    """'3 hours 9 minutes', '1 day 2 hours', '40 minutes': how long, in words, to the minute."""
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise ValueError("a span is a whole, non-negative number of seconds")
    minutes = seconds // 60
    days, rest = divmod(minutes, 24 * 60)
    hours, minutes = divmod(rest, 60)
    units = [(days, "day"), (hours, "hour"), (minutes, "minute")]
    words = [f"{n} {unit}{'' if n == 1 else 's'}" for n, unit in units if n]
    # Days and hours are enough once a day has gone by.
    return " ".join(words[:2]) if words else "less than a minute"
