"""The moon and the tides (D57, D59): pure functions of the time.

The moon's phase comes from the mean synodic month, counted from a known new
moon. The tide is a simple semi-diurnal model: two highs a day, about 50
minutes later each day, stronger near new and full moon (spring tides).
"""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

SYNODIC_DAYS = 29.530588853
# A known new moon: 2000-01-06 18:14 UTC.
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
PHASES = (
    "new moon",
    "waxing crescent",
    "first quarter",
    "waxing gibbous",
    "full moon",
    "waning gibbous",
    "last quarter",
    "waning crescent",
)
# Within this many days of new or full moon, tides run high and low: spring tides.
SPRING_WINDOW_DAYS = 2.0

TIDE_PERIOD_HOURS = 12.4206  # the principal lunar semi-diurnal tide
# Hours from the epoch new moon (18:14 UTC) to a high water: 13:00 UTC that day.
HIGH_WATER_OFFSET_HOURS = -5.23
TURNING_RADIANS = 0.4  # about 47 minutes either side of high or low water


class TideState(StrEnum):
    LOW = "low"
    FLOODING = "flooding"  # rising
    HIGH = "high"
    EBBING = "ebbing"  # falling


# Conditions a place's tide rules can name.
TIDE_CONDITIONS = frozenset(
    {"low", "flooding", "high", "ebbing", "turning", "spring", "spring-high", "spring-low"}
)


@dataclass(frozen=True)
class Moon:
    phase: str
    age_days: float
    illumination: float  # 0 at new moon, 1 at full

    @property
    def spring(self) -> bool:
        half = SYNODIC_DAYS / 2
        return min(self.age_days, SYNODIC_DAYS - self.age_days, abs(self.age_days - half)) <= (
            SPRING_WINDOW_DAYS
        )


@dataclass(frozen=True)
class Tide:
    state: TideState
    height: float  # -1.35 to +1.35, relative to mean water
    turning: bool
    spring: bool
    next_high: datetime
    next_low: datetime

    @property
    def conditions(self) -> frozenset[str]:
        found = {self.state.value}
        if self.turning:
            found.add("turning")
        if self.spring:
            found.add("spring")
            if self.state in (TideState.HIGH, TideState.LOW):
                found.add(f"spring-{self.state.value}")
        return frozenset(found)


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("times must be timezone-aware")
    return moment


def moon(moment: datetime) -> Moon:
    days = (_aware(moment) - NEW_MOON_EPOCH).total_seconds() / 86_400
    age = days % SYNODIC_DAYS
    index = int(age / SYNODIC_DAYS * 8 + 0.5) % 8
    illumination = (1 - math.cos(2 * math.pi * age / SYNODIC_DAYS)) / 2
    return Moon(PHASES[index], age, round(illumination, 3))


def _tide_angle(moment: datetime) -> float:
    """0 at high water, pi at low water.

    A 12.42-hour period carries the daily 50-minute drift on its own; the offset
    puts high water near 13:00 UTC (9 am city time) on the day of a new moon.
    """
    hours = (_aware(moment) - NEW_MOON_EPOCH).total_seconds() / 3600
    return 2 * math.pi * ((hours - HIGH_WATER_OFFSET_HOURS) / TIDE_PERIOD_HOURS % 1)


def _next_angle(moment: datetime, target: float) -> datetime:
    angle = _tide_angle(moment)
    ahead = (target - angle) % (2 * math.pi)
    if ahead < 1e-6:
        ahead = 2 * math.pi
    return moment + timedelta(hours=ahead / (2 * math.pi) * TIDE_PERIOD_HOURS)


def tide(moment: datetime) -> Tide:
    angle = _tide_angle(moment)
    phase = moon(moment)
    amplitude = 1 + 0.35 * math.cos(4 * math.pi * phase.age_days / SYNODIC_DAYS)
    height = math.cos(angle) * amplitude
    if angle <= math.pi / 4 or angle >= 7 * math.pi / 4:
        state = TideState.HIGH
    elif angle < 3 * math.pi / 4:
        state = TideState.EBBING
    elif angle <= 5 * math.pi / 4:
        state = TideState.LOW
    else:
        state = TideState.FLOODING
    turning = min(angle, abs(angle - math.pi), 2 * math.pi - angle) <= TURNING_RADIANS
    return Tide(
        state=state,
        height=round(height, 2),
        turning=turning,
        spring=phase.spring,
        next_high=_next_angle(moment, 0.0),
        next_low=_next_angle(moment, math.pi),
    )
