"""The social graph's rules (D127-D130, D141-D143): which feelings a tension or an
alliance may move, what counts as a betrayal, when a grudge fades, and the amends roll.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from new_vesper.rules.attitudes import ATTITUDE_MAX, ATTITUDE_MIN, Axis
from new_vesper.rules.dice import Rng, roll_2d6
from new_vesper.rules.errors import RulesError, parse_enum, require_range
from new_vesper.rules.resolver import Tier, tier_for_total

# A one-step grudge that is not a betrayal fades after this long unless renewed (D129).
FADE_AFTER = timedelta(days=7)
# After refused amends, no new amends between the two for this long (D142).
REFUSED_FOR = timedelta(days=7)
# Trust at or above this, just before learning, makes it a betrayal (D143).
BETRAYAL_TRUST = 1
# Axes a grudge is held on: a drop in either is a grudge; fear is not (D143).
GRUDGE_AXES = frozenset({Axis.TRUST, Axis.FONDNESS})


class BondKind(StrEnum):
    TENSION = "tension"
    ALLIANCE = "alliance"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"


class AmendsOutcome(StrEnum):
    ACCEPTED = "accepted"  # 10+
    ON_CONDITION = "on_condition"  # 7-9
    REFUSED = "refused"  # 6-


TIER_OUTCOME: dict[Tier, AmendsOutcome] = {
    Tier.CLEAN: AmendsOutcome.ACCEPTED,
    Tier.COST: AmendsOutcome.ON_CONDITION,
    Tier.CITY_MOVES: AmendsOutcome.REFUSED,
}

# What learning of the other's part may do, per kind of bond (D141).
ALLOWED: dict[BondKind, frozenset[tuple[Axis, Direction]]] = {
    BondKind.TENSION: frozenset(
        {(Axis.TRUST, Direction.DOWN), (Axis.FONDNESS, Direction.DOWN), (Axis.FEAR, Direction.UP)}
    ),
    BondKind.ALLIANCE: frozenset({(Axis.TRUST, Direction.UP), (Axis.FONDNESS, Direction.UP)}),
}


def parse_direction(value: object) -> Direction:
    return parse_enum(Direction, value, "direction")


def check_feeling(kind: BondKind, axis: Axis, direction: Direction) -> int:
    """The step a bond allows on this axis and direction, as +1 or -1; refused otherwise."""
    if (axis, direction) not in ALLOWED[kind]:
        allowed = ", ".join(sorted(f"{a.value} {d.value}" for a, d in ALLOWED[kind]))
        raise RulesError(f"learning of a {kind.value} may move only: {allowed}")
    return 1 if direction is Direction.UP else -1


def makes_grudge(kind: BondKind, axis: Axis, delta: int) -> bool:
    """A trust or fondness drop from learning of a tension is a grudge (D143)."""
    return kind is BondKind.TENSION and axis in GRUDGE_AXES and delta < 0


def is_betrayal(trust_before: int, allied: bool) -> bool:
    """They trusted the other just before learning, or the two shared an alliance (D143)."""
    require_range(trust_before, "trust", ATTITUDE_MIN, ATTITUDE_MAX)
    return allied or trust_before >= BETRAYAL_TRUST


def needs_amends(depth: int, betrayal: bool) -> bool:
    """Two steps or more, or a betrayal, never fade on their own (D129)."""
    return betrayal or depth >= 2


def fades(depth: int, betrayal: bool, renewed_at: datetime, now: datetime) -> bool:
    """A one-step grudge, not a betrayal, fades a week after it was last renewed."""
    return not needs_amends(depth, betrayal) and now - renewed_at >= FADE_AFTER


def recovery_axis(trust_steps: int, fondness_steps: int) -> Axis:
    """The axis a step comes back to when a grudge ends: the deeper one, trust on a tie."""
    if trust_steps + fondness_steps <= 0:
        raise RulesError("a grudge has at least one step")
    return Axis.FONDNESS if fondness_steps > trust_steps else Axis.TRUST


@dataclass(frozen=True)
class AmendsRoll:
    dice: tuple[int, int]
    fondness: int
    total: int
    outcome: AmendsOutcome


def roll_amends(fondness: int, rng: Rng) -> AmendsRoll:
    """2d6 plus the wronged NPC's fondness toward the wrongdoer, no rung (D142)."""
    require_range(fondness, "fondness", ATTITUDE_MIN, ATTITUDE_MAX)
    dice = roll_2d6(rng)
    total = sum(dice) + fondness
    return AmendsRoll(dice, fondness, total, TIER_OUTCOME[tier_for_total(total)])
