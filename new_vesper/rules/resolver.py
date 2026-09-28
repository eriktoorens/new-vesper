"""The 2d6 resolver: 2d6 + stat + difficulty modifier, three tiers."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.dice import Rng, roll_2d6
from new_vesper.rules.errors import parse_enum, require_range
from new_vesper.rules.stats import ADVANCED_STAT_CAP, STAT_MIN
from new_vesper.rules.tracks import CRITICAL_PENALTY


class Difficulty(StrEnum):
    ROUTINE = "routine"
    RISKY = "risky"
    HARD = "hard"
    DESPERATE = "desperate"


DIFFICULTY_MODIFIER: dict[Difficulty, int] = {
    Difficulty.ROUTINE: 1,
    Difficulty.RISKY: 0,
    Difficulty.HARD: -1,
    Difficulty.DESPERATE: -2,
}


class Tier(StrEnum):
    CLEAN = "clean"  # 10+: you get what you wanted
    COST = "cost"  # 7-9: you get it, but lose something
    CITY_MOVES = "city_moves"  # 6-: the DM makes a move from the allowed list


# Higher rank is a better outcome for the roller.
TIER_RANK: dict[Tier, int] = {Tier.CITY_MOVES: 0, Tier.COST: 1, Tier.CLEAN: 2}

CLEAN_THRESHOLD = 10
COST_THRESHOLD = 7

# The lowest effective stat is the floor with the Critical penalty applied;
# the highest is the advanced-knack cap.
EFFECTIVE_STAT_MIN = STAT_MIN - CRITICAL_PENALTY
EFFECTIVE_STAT_MAX = ADVANCED_STAT_CAP
# Knack balance budget: at most +1 to a roll.
MAX_ROLL_BONUS = 1


@dataclass(frozen=True)
class RollResult:
    dice: tuple[int, int]
    stat_value: int
    modifier: int
    bonus: int
    total: int
    tier: Tier


def parse_difficulty(value: object) -> Difficulty:
    return parse_enum(Difficulty, value, "difficulty")


def tier_for_total(total: int) -> Tier:
    if total >= CLEAN_THRESHOLD:
        return Tier.CLEAN
    if total >= COST_THRESHOLD:
        return Tier.COST
    return Tier.CITY_MOVES


def resolve(stat_value: int, difficulty: Difficulty, rng: Rng, bonus: int = 0) -> RollResult:
    """Roll 2d6 + effective stat + difficulty modifier (+ a knack bonus of at most +1).

    ``stat_value`` is the effective stat, after conditions such as Wounded.
    """
    require_range(stat_value, "stat value", EFFECTIVE_STAT_MIN, EFFECTIVE_STAT_MAX)
    require_range(bonus, "roll bonus", 0, MAX_ROLL_BONUS)
    difficulty = parse_difficulty(difficulty)
    modifier = DIFFICULTY_MODIFIER[difficulty]
    dice = roll_2d6(rng)
    total = sum(dice) + stat_value + modifier + bonus
    return RollResult(
        dice=dice,
        stat_value=stat_value,
        modifier=modifier,
        bonus=bonus,
        total=total,
        tier=tier_for_total(total),
    )
