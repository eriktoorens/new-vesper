"""Magic: bargaining with attention. No slots, no mana."""

from enum import StrEnum

from new_vesper.rules.errors import RulesError, parse_enum
from new_vesper.rules.resolver import Difficulty, parse_difficulty
from new_vesper.rules.stats import Stat, parse_stat


class MagicCost(StrEnum):
    """Costs the DM may pick on a 7-9 casting."""

    FADE_TICK = "fade_tick"  # one box of Fade
    SIDE_EFFECT = "side_effect"
    FAVOR_OWED = "favor_owed"  # recorded in the favor ledger


FADE_TICK_BOXES = 1
# Raw magic without a knack is always Desperate.
RAW_MAGIC_DIFFICULTY = Difficulty.DESPERATE


def parse_magic_cost(value: object) -> MagicCost:
    return parse_enum(MagicCost, value, "magic cost")


def casting_stat(stat: object, tech_magic: bool) -> Stat:
    """Casting is a Weird roll; tech-magic may use Wire instead."""
    parsed = parse_stat(stat)
    if parsed is Stat.WEIRD or (parsed is Stat.WIRE and tech_magic):
        return parsed
    if parsed is Stat.WIRE:
        raise RulesError("wire casts only tech-magic")
    raise RulesError(f"casting uses weird (or wire for tech-magic), not {parsed}")


def casting_difficulty(has_knack: bool, requested: object) -> Difficulty:
    """With a knack the DM's rung stands; without one the working is Desperate."""
    parsed = parse_difficulty(requested)
    return parsed if has_knack else RAW_MAGIC_DIFFICULTY
