import pytest

from new_vesper.rules.consequences import (
    ConsequenceType,
    allowed,
    validate_consequence,
)
from new_vesper.rules.errors import RulesError
from new_vesper.rules.resolver import Tier

C = ConsequenceType


def test_clean_success_allows_nothing() -> None:
    assert allowed(Tier.CLEAN, magic=False) == {}
    with pytest.raises(RulesError, match="clean success"):
        validate_consequence(Tier.CLEAN, False, "deal_harm", 1)


def test_cost_list() -> None:
    assert set(allowed(Tier.COST, magic=False)) == {
        C.TAKE_SOMETHING,
        C.DEAL_HARM,
        C.ADD_FADE,
        C.DARK_ENCROACHES,
        C.NARRATIVE_COST,
    }
    assert set(allowed(Tier.COST, magic=False).values()) == {1}


def test_magic_cost_list() -> None:
    assert set(allowed(Tier.COST, magic=True)) == {C.ADD_FADE, C.SIDE_EFFECT, C.FAVOR_OWED}


def test_cost_caps_harm_at_one() -> None:
    assert validate_consequence(Tier.COST, False, "deal_harm", 1).magnitude == 1
    with pytest.raises(RulesError):
        validate_consequence(Tier.COST, False, "deal_harm", 2)


@pytest.mark.parametrize("move", ["separate_them", "advance_threat_clock", "favor_owed"])
def test_moves_are_not_costs(move: str) -> None:
    with pytest.raises(RulesError, match="not an allowed cost"):
        validate_consequence(Tier.COST, False, move, 1)


def test_magic_cost_rejects_ordinary_costs() -> None:
    with pytest.raises(RulesError, match="magic cost"):
        validate_consequence(Tier.COST, True, "take_something", 1)


def test_city_moves_allows_the_eight_moves() -> None:
    limits = allowed(Tier.CITY_MOVES, magic=False)
    assert len(limits) == 8
    assert limits[C.DEAL_HARM] == 3
    assert limits[C.DARK_ENCROACHES] == 1
    assert validate_consequence(Tier.CITY_MOVES, False, "deal_harm", 3).magnitude == 3
    with pytest.raises(RulesError):
        validate_consequence(Tier.CITY_MOVES, False, "deal_harm", 4)
    with pytest.raises(RulesError):
        validate_consequence(Tier.CITY_MOVES, False, "narrative_cost", 1)


@pytest.mark.parametrize(
    ("kind", "magnitude"),
    [
        ("kill", 1),
        ("deal_harm; and 6 more", 1),
        (None, 1),
        ("deal_harm", "3"),
        ("deal_harm", 0),
        ("deal_harm", True),
    ],
)
def test_malformed_consequences_rejected(kind: object, magnitude: object) -> None:
    with pytest.raises(RulesError):
        validate_consequence(Tier.CITY_MOVES, False, kind, magnitude)
