"""The five stats, their caps and the starting array."""

from collections.abc import Mapping
from enum import StrEnum

from new_vesper.rules.errors import RulesError, parse_enum, require_int


class Stat(StrEnum):
    STEEL = "steel"  # violence, endurance, chrome
    SLICK = "slick"  # stealth, grace, lies
    WIRE = "wire"  # tech, hacking, the network
    WEIRD = "weird"  # magic, spirits, bargains with gods
    HEART = "heart"  # connection, conviction, being remembered


STAT_MIN = -1
STAT_CAP = 3
# One stat can reach +4 through a level-10 advanced knack.
ADVANCED_STAT_CAP = 4
ADVANCED_STAT_MIN_LEVEL = 10

# Creation: assign +2, +1, +1, 0, -1 to the five stats.
STARTING_ARRAY: tuple[int, ...] = (2, 1, 1, 0, -1)


def parse_stat(value: object) -> Stat:
    return parse_enum(Stat, value, "stat")


def stat_cap(stat: Stat, boosted_stat: Stat | None) -> int:
    """The highest value ``stat`` may reach for this character."""
    return ADVANCED_STAT_CAP if stat is boosted_stat else STAT_CAP


def validate_starting_stats(stats: Mapping[Stat, int]) -> dict[Stat, int]:
    """Check that ``stats`` is the starting array assigned to all five stats."""
    if set(stats) != set(Stat):
        raise RulesError("starting stats must assign exactly the five stats")
    values = [require_int(stats[stat], f"{stat} value") for stat in Stat]
    if sorted(values, reverse=True) != list(STARTING_ARRAY):
        raise RulesError("starting stats must use the array +2, +1, +1, 0, -1")
    return {stat: stats[stat] for stat in Stat}


def validate_stats(stats: Mapping[Stat, int], boosted_stat: Stat | None) -> dict[Stat, int]:
    """Check that every stat is present and within its floor and cap."""
    if set(stats) != set(Stat):
        raise RulesError("stats must assign exactly the five stats")
    for stat in Stat:
        value = require_int(stats[stat], f"{stat} value")
        cap = stat_cap(stat, boosted_stat)
        if not STAT_MIN <= value <= cap:
            raise RulesError(f"{stat} must be between {STAT_MIN} and {cap}, got {value}")
    return {stat: stats[stat] for stat in Stat}
