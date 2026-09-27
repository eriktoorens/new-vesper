"""Player versus player: opposed rolls, where the defender always has agency."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import RulesError, require_int
from new_vesper.rules.resolver import TIER_RANK, Difficulty, RollResult, resolve


class OpposedOutcome(StrEnum):
    ATTACKER = "attacker"
    DEFENDER = "defender"


@dataclass(frozen=True)
class OpposedResult:
    attacker: RollResult
    defender: RollResult
    outcome: OpposedOutcome


def opposed_roll(
    attacker_stat: int,
    attacker_difficulty: Difficulty,
    defender_stat: int,
    defender_difficulty: Difficulty,
    rng: Rng,
    attacker_bonus: int = 0,
    defender_bonus: int = 0,
) -> OpposedResult:
    """Both players roll; the better tier wins, and the defender holds a tie (D5)."""
    attacker = resolve(attacker_stat, attacker_difficulty, rng, attacker_bonus)
    defender = resolve(defender_stat, defender_difficulty, rng, defender_bonus)
    a, d = TIER_RANK[attacker.tier], TIER_RANK[defender.tier]
    outcome = OpposedOutcome.ATTACKER if a > d else OpposedOutcome.DEFENDER
    return OpposedResult(attacker=attacker, defender=defender, outcome=outcome)


def check_pvp_state_change(at_haven: bool, target_online: bool) -> None:
    """Havens are safe, and offline characters cannot be harmed."""
    if at_haven:
        raise RulesError("no PvP state change at a haven")
    if not target_online:
        raise RulesError("offline characters cannot be harmed")


# Preying on the weak (D16): Fade to the attacker per PvP consequence, by level gap.
PREYING_GAPS: tuple[tuple[int, int], ...] = ((5, 2), (3, 1))


def preying_fade(attacker_level: int, target_level: int) -> int:
    """Fade the attacker takes for a PvP consequence against a lower-level target."""
    gap = require_int(attacker_level, "attacker level") - require_int(target_level, "target level")
    for min_gap, fade in PREYING_GAPS:
        if gap >= min_gap:
            return fade
    return 0
