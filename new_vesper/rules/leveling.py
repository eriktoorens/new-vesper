"""Leveling: reaching level N+1 costs 5 + N XP; every fifth level is a milestone."""

from dataclasses import dataclass, replace
from enum import StrEnum

from new_vesper.rules.character import Sheet, validate_id
from new_vesper.rules.errors import RulesError, parse_enum, require_int
from new_vesper.rules.stats import ADVANCED_STAT_MIN_LEVEL, Stat, parse_stat, stat_cap

XP_BASE_COST = 5
MILESTONE_EVERY = 5


class LevelChoice(StrEnum):
    NEW_KNACK = "new_knack"
    STAT_BOOST = "stat_boost"  # +1 to a stat, cap +3
    HEAL_SCAR = "heal_scar"


class MilestoneChoice(StrEnum):
    ADVANCED_KNACK = "advanced_knack"
    ORIGIN_EVOLUTION = "origin_evolution"


@dataclass(frozen=True)
class LevelUpRequest:
    choice: LevelChoice | str
    stat: Stat | str | None = None  # for STAT_BOOST
    knack: str | None = None  # for NEW_KNACK
    scar: str | None = None  # for HEAL_SCAR
    milestone: MilestoneChoice | str | None = None  # required on every fifth level
    milestone_id: str | None = None  # the advanced knack or origin evolution taken
    # An advanced knack from level 10 may let one stat reach +4.
    boost_stat: Stat | str | None = None


def xp_to_advance(level: int) -> int:
    """XP needed to go from ``level`` to ``level + 1``."""
    if require_int(level, "level") < 1:
        raise RulesError("level must be at least 1")
    return XP_BASE_COST + level


def is_milestone(level: int) -> bool:
    """Whether reaching ``level`` unlocks an advanced knack or origin evolution."""
    return require_int(level, "level") % MILESTONE_EVERY == 0


def can_level_up(sheet: Sheet) -> bool:
    return not sheet.fallen and sheet.xp >= xp_to_advance(sheet.level)


def _apply_milestone(sheet: Sheet, request: LevelUpRequest, new_level: int) -> Sheet:
    if not is_milestone(new_level):
        if request.milestone is not None or request.milestone_id is not None:
            raise RulesError(f"level {new_level} is not a milestone")
        if request.boost_stat is not None:
            raise RulesError("a stat can pass +3 only through an advanced knack")
        return sheet
    if request.milestone is None:
        raise RulesError(f"level {new_level} is a milestone: pick an advanced knack or evolution")
    milestone = parse_enum(MilestoneChoice, request.milestone, "milestone choice")
    item = validate_id(request.milestone_id, str(milestone))
    if milestone is MilestoneChoice.ORIGIN_EVOLUTION:
        if request.boost_stat is not None:
            raise RulesError("only an advanced knack can let a stat pass +3")
        if item in sheet.origin_evolutions:
            raise RulesError(f"already evolved {item!r}")
        return replace(sheet, origin_evolutions=(*sheet.origin_evolutions, item))
    if item in sheet.advanced_knacks:
        raise RulesError(f"already has advanced knack {item!r}")
    sheet = replace(sheet, advanced_knacks=(*sheet.advanced_knacks, item))
    if request.boost_stat is None:
        return sheet
    if new_level < ADVANCED_STAT_MIN_LEVEL:
        raise RulesError(f"a stat can reach +4 only from level {ADVANCED_STAT_MIN_LEVEL}")
    if sheet.boosted_stat is not None:
        raise RulesError("only one stat can reach +4")
    return replace(sheet, boosted_stat=parse_stat(request.boost_stat))


def _apply_choice(sheet: Sheet, request: LevelUpRequest) -> Sheet:
    choice = parse_enum(LevelChoice, request.choice, "level choice")
    extras = {
        LevelChoice.NEW_KNACK: ("knack", request.knack),
        LevelChoice.STAT_BOOST: ("stat", request.stat),
        LevelChoice.HEAL_SCAR: ("scar", request.scar),
    }
    for other, (name, value) in extras.items():
        if other is not choice and value is not None:
            raise RulesError(f"{name} does not apply to {choice}")

    if choice is LevelChoice.NEW_KNACK:
        knack = validate_id(request.knack, "knack")
        if knack in sheet.knacks:
            raise RulesError(f"already has knack {knack!r}")
        return replace(sheet, knacks=(*sheet.knacks, knack))
    if choice is LevelChoice.STAT_BOOST:
        stat = parse_stat(request.stat)
        cap = stat_cap(stat, sheet.boosted_stat)
        if sheet.stats[stat] >= cap:
            raise RulesError(f"{stat} is already at its cap of +{cap}")
        return replace(sheet, stats={**sheet.stats, stat: sheet.stats[stat] + 1})
    scar = validate_id(request.scar, "scar")
    if scar not in sheet.scars:
        raise RulesError(f"no scar {scar!r} to heal")
    return replace(sheet, scars=tuple(s for s in sheet.scars if s != scar))


def level_up(sheet: Sheet, request: LevelUpRequest) -> Sheet:
    """Spend XP to gain a level. Validates everything before returning a new sheet."""
    if sheet.fallen:
        raise RulesError("this character has fallen")
    cost = xp_to_advance(sheet.level)
    if sheet.xp < cost:
        raise RulesError(f"level {sheet.level + 1} costs {cost} XP; have {sheet.xp}")
    new_level = sheet.level + 1
    # The milestone lands first, so a level-10 advanced knack can open +4 for
    # the same level's stat boost.
    sheet = _apply_milestone(sheet, request, new_level)
    sheet = _apply_choice(sheet, request)
    return replace(sheet, level=new_level, xp=sheet.xp - cost)
