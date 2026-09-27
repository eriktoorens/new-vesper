import pytest

from new_vesper.rules.errors import RulesError
from new_vesper.rules.pvp import OpposedOutcome, check_pvp_state_change, opposed_roll
from new_vesper.rules.resolver import Difficulty, Tier
from tests.rules.conftest import FixedDice

RISKY = Difficulty.RISKY


def test_attacker_wins_on_better_tier() -> None:
    result = opposed_roll(0, RISKY, 0, RISKY, FixedDice([6, 5, 2, 2]))
    assert result.attacker.tier is Tier.CLEAN
    assert result.defender.tier is Tier.CITY_MOVES
    assert result.outcome is OpposedOutcome.ATTACKER


def test_defender_wins_on_better_tier() -> None:
    result = opposed_roll(0, RISKY, 2, RISKY, FixedDice([4, 4, 4, 4]))
    assert result.attacker.tier is Tier.COST
    assert result.defender.tier is Tier.CLEAN
    assert result.outcome is OpposedOutcome.DEFENDER


def test_same_tier_is_a_tie_even_with_different_totals() -> None:
    result = opposed_roll(0, RISKY, 0, RISKY, FixedDice([6, 6, 5, 5]))
    assert (result.attacker.total, result.defender.total) == (12, 10)
    assert result.outcome is OpposedOutcome.TIE


def test_each_side_uses_its_own_difficulty() -> None:
    result = opposed_roll(0, Difficulty.ROUTINE, 0, Difficulty.DESPERATE, FixedDice([3, 3, 3, 3]))
    assert result.attacker.total == 7
    assert result.defender.total == 4


def test_no_pvp_state_change_at_haven() -> None:
    with pytest.raises(RulesError):
        check_pvp_state_change(at_haven=True, target_online=True)


def test_offline_target_cannot_be_harmed() -> None:
    with pytest.raises(RulesError):
        check_pvp_state_change(at_haven=False, target_online=False)


def test_pvp_allowed_elsewhere() -> None:
    check_pvp_state_change(at_haven=False, target_online=True)
