"""Player versus player: opposed rolls, where the defender always has agency."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import RulesError
from new_vesper.rules.resolver import TIER_RANK, Difficulty, RollResult, resolve


class OpposedOutcome(StrEnum):
    ATTACKER = "attacker"
    DEFENDER = "defender"
    # The design doc compares tiers and says nothing about equal tiers, so a
    # tie is reported as such for the DM and a later rule to resolve.
    TIE = "tie"


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
    """Both players roll; the better tier wins."""
    attacker = resolve(attacker_stat, attacker_difficulty, rng, attacker_bonus)
    defender = resolve(defender_stat, defender_difficulty, rng, defender_bonus)
    a, d = TIER_RANK[attacker.tier], TIER_RANK[defender.tier]
    if a > d:
        outcome = OpposedOutcome.ATTACKER
    elif d > a:
        outcome = OpposedOutcome.DEFENDER
    else:
        outcome = OpposedOutcome.TIE
    return OpposedResult(attacker=attacker, defender=defender, outcome=outcome)


def check_pvp_state_change(at_haven: bool, target_online: bool) -> None:
    """Havens are safe, and offline characters cannot be harmed."""
    if at_haven:
        raise RulesError("no PvP state change at a haven")
    if not target_online:
        raise RulesError("offline characters cannot be harmed")
