import pytest

from new_vesper.rules.errors import RulesError
from new_vesper.rules.magic import (
    MagicCost,
    casting_difficulty,
    casting_stat,
    parse_magic_cost,
)
from new_vesper.rules.resolver import Difficulty
from new_vesper.rules.stats import Stat


def test_casting_is_weird() -> None:
    assert casting_stat("weird", tech_magic=False) is Stat.WEIRD
    assert casting_stat("weird", tech_magic=True) is Stat.WEIRD


def test_wire_only_for_tech_magic() -> None:
    assert casting_stat("wire", tech_magic=True) is Stat.WIRE
    with pytest.raises(RulesError):
        casting_stat("wire", tech_magic=False)


@pytest.mark.parametrize("stat", ["steel", "heart", "slick", "mana", 3])
def test_other_stats_cannot_cast(stat: object) -> None:
    with pytest.raises(RulesError):
        casting_stat(stat, tech_magic=True)


def test_raw_magic_is_desperate() -> None:
    assert casting_difficulty(False, "routine") is Difficulty.DESPERATE
    assert casting_difficulty(True, "routine") is Difficulty.ROUTINE


def test_raw_magic_still_validates_rung() -> None:
    with pytest.raises(RulesError):
        casting_difficulty(False, "trivial")


def test_magic_costs() -> None:
    assert {c.value for c in MagicCost} == {"fade_tick", "side_effect", "favor_owed"}
    assert parse_magic_cost("favor_owed") is MagicCost.FAVOR_OWED
    with pytest.raises(RulesError):
        parse_magic_cost("nothing")
