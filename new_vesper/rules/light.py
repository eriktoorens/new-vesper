"""Region Light: 0-10. At zero the region falls into Old Vesper."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import RulesError, parse_enum, require_int, require_range

LIGHT_MIN = 0
LIGHT_MAX = 10
# The dark encroaches: region Light -1.
ENCROACH_STEP = -1
# Neglected regions lose 1 per in-game week.
NEGLECT_STEP_PER_WEEK = -1


class DeedSize(StrEnum):
    DEED = "deed"  # +/-1
    MAJOR = "major"  # +/-2


DEED_STEP: dict[DeedSize, int] = {DeedSize.DEED: 1, DeedSize.MAJOR: 2}


class Direction(StrEnum):
    RAISE = "raise"
    LOWER = "lower"


@dataclass(frozen=True)
class LightChange:
    before: int
    after: int
    fell: bool  # this change took the region to zero: it falls into Old Vesper


def parse_deed_size(value: object) -> DeedSize:
    return parse_enum(DeedSize, value, "deed size")


def parse_direction(value: object) -> Direction:
    return parse_enum(Direction, value, "direction")


def _change(current: int, delta: int) -> LightChange:
    require_range(current, "region light", LIGHT_MIN, LIGHT_MAX)
    after = min(LIGHT_MAX, max(LIGHT_MIN, current + delta))
    return LightChange(before=current, after=after, fell=after == LIGHT_MIN and current > 0)


def deed_step(direction: object, size: object) -> int:
    step = DEED_STEP[parse_deed_size(size)]
    return step if parse_direction(direction) is Direction.RAISE else -step


def apply_deed(current: int, direction: object, size: object) -> LightChange:
    """A deed moves Light by 1, a major deed by 2, clamped to 0..10."""
    return _change(current, deed_step(direction, size))


def encroach(current: int) -> LightChange:
    """The dark encroaches: Light -1."""
    return _change(current, ENCROACH_STEP)


def apply_neglect(current: int, weeks: int) -> LightChange:
    """A neglected region loses 1 Light per in-game week."""
    if require_int(weeks, "weeks") < 0:
        raise RulesError(f"weeks must not be negative, got {weeks}")
    return _change(current, NEGLECT_STEP_PER_WEEK * weeks)


def has_fallen(light: int) -> bool:
    return require_range(light, "region light", LIGHT_MIN, LIGHT_MAX) == LIGHT_MIN
