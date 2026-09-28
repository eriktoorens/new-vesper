"""Bodily needs (D83-D89): hunger, thirst, tiredness, cold and heat.

Each need runs 0-3. It rises on the city clock while the character is online
(cold and heat only while exposed to them, easing otherwise). Levels 2 and 3
take -1 and -2 from two stats each; reaching the worst level, and every further
step there, costs a box of Harm (Fade for tiredness). Dice never kill: a full
Harm track still ends in the player's choice, Fall or Endure.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import parse_enum, require_int, require_range
from new_vesper.rules.resolver import EFFECTIVE_STAT_MIN
from new_vesper.rules.stats import Stat
from new_vesper.rules.tracks import Track

NEED_MAX = 3
HOUR = 3600


class Need(StrEnum):
    HUNGER = "hunger"
    THIRST = "thirst"
    TIRED = "tired"
    COLD = "cold"
    HEAT = "heat"


class Exposure(StrEnum):
    """What the weather and the place are doing to a body right now (D86)."""

    COLD = "cold"
    HOT = "hot"
    NONE = "none"


class Climate(StrEnum):
    """How a place shields a body from the weather (D86)."""

    SHELTERED = "sheltered"  # indoors: the weather doesn't reach you
    EXPOSED = "exposed"  # the weather does
    COLD = "cold"  # cold whatever the weather, like a drowned station


# Needs that rise whatever the weather, and those that follow exposure.
CLOCK_NEEDS = (Need.HUNGER, Need.THIRST, Need.TIRED)
EXPOSURE_NEEDS = {Need.COLD: Exposure.COLD, Need.HEAT: Exposure.HOT}

# Seconds of online time per step up (D85). Tuning values, for playtest.
STEP_SECONDS: Mapping[Need, int] = {
    Need.THIRST: 3 * HOUR,
    Need.HUNGER: 4 * HOUR,
    Need.TIRED: 6 * HOUR,
    Need.COLD: 1 * HOUR,
    Need.HEAT: 1 * HOUR,
}
# Out of the cold (or heat), a body recovers one step this fast.
RECOVER_SECONDS = HOUR // 2

# Two stats each need wears down (D84).
AFFECTS: Mapping[Need, tuple[Stat, Stat]] = {
    Need.HUNGER: (Stat.STEEL, Stat.HEART),
    Need.THIRST: (Stat.STEEL, Stat.WIRE),
    Need.TIRED: (Stat.SLICK, Stat.WIRE),
    Need.COLD: (Stat.STEEL, Stat.SLICK),
    Need.HEAT: (Stat.STEEL, Stat.HEART),
}
# Penalty by level: nothing at 0-1, -1 at 2, -2 at the worst.
PENALTY = (0, 0, 1, 2)
# What the worst level costs, per step spent there.
WORST_TRACK: Mapping[Need, Track] = {
    Need.HUNGER: Track.HARM,
    Need.THIRST: Track.HARM,
    Need.TIRED: Track.FADE,
    Need.COLD: Track.HARM,
    Need.HEAT: Track.HARM,
}
WORDS: Mapping[Need, tuple[str, str, str, str]] = {
    Need.HUNGER: ("fed", "peckish", "hungry", "starving"),
    Need.THIRST: ("slaked", "thirsty", "parched", "dehydrated"),
    Need.TIRED: ("rested", "tired", "exhausted", "dead on their feet"),
    Need.COLD: ("warm enough", "chilled", "cold", "freezing"),
    Need.HEAT: ("cool enough", "hot", "overheated", "heatstruck"),
}


def parse_need(value: object) -> Need:
    return parse_enum(Need, value, "need")


@dataclass(frozen=True)
class NeedState:
    level: int = 0
    accrued: int = 0  # seconds counted toward the next step

    def __post_init__(self) -> None:
        require_range(self.level, "need level", 0, NEED_MAX)
        require_int(self.accrued, "accrued seconds")
        if self.accrued < 0:
            raise ValueError("accrued seconds cannot be negative")


@dataclass(frozen=True)
class NeedChange:
    before: NeedState
    after: NeedState
    worst_steps: int  # boxes of Harm or Fade owed for steps at the worst level


def rising(need: Need, exposure: Exposure) -> bool:
    """Whether a need is getting worse right now."""
    return need in CLOCK_NEEDS or EXPOSURE_NEEDS[need] is exposure


def advance(need: Need, state: NeedState, seconds: int, exposure: Exposure) -> NeedChange:
    """Let ``seconds`` of online time pass for one need.

    Rising needs climb a step per interval; reaching the worst level and each
    further step there owes one box. Cold and heat ease off when not exposed.
    """
    elapsed = require_int(seconds, "seconds")
    if elapsed < 0:
        raise ValueError("time does not run backwards")
    if rising(need, exposure):
        step = STEP_SECONDS[need]
        total = state.accrued + elapsed
        level, owed = state.level, 0
        for _ in range(total // step):
            level = min(NEED_MAX, level + 1)
            if level == NEED_MAX:
                owed += 1
        return NeedChange(state, NeedState(level, total % step), owed)
    if state.level == 0:
        return NeedChange(state, NeedState(), 0)
    total = state.accrued + elapsed
    level = max(0, state.level - total // RECOVER_SECONDS)
    return NeedChange(state, NeedState(level, 0 if level == 0 else total % RECOVER_SECONDS), 0)


def penalty(stat: Stat, levels: Mapping[Need, int]) -> int:
    """How much the character's needs take off a stat, stacked across needs."""
    return sum(PENALTY[level] for need, level in levels.items() if stat in AFFECTS[need])


def exposure(climate: Climate, weather: Exposure | None, season: Exposure | None) -> Exposure:
    """What a place is doing to a body: the weather's own feel wins over the season's."""
    if climate is Climate.SHELTERED:
        return Exposure.NONE
    if climate is Climate.COLD:
        return Exposure.COLD
    return weather or season or Exposure.NONE


def roll_stat(value: int, stat: Stat, levels: Mapping[Need, int]) -> int:
    """A stat after needs, on top of Harm; never below the lowest roll stat, -3 (D84)."""
    return max(EFFECTIVE_STAT_MIN, value - penalty(stat, levels))


def words(need: Need, level: int) -> str:
    return WORDS[need][require_range(level, "need level", 0, NEED_MAX)]
