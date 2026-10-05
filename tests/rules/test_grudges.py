"""The social graph's rules: bonds, betrayal, fading grudges and amends (D141-D143)."""

from datetime import UTC, datetime

import pytest

from new_vesper.rules.attitudes import Axis
from new_vesper.rules.errors import RulesError
from new_vesper.rules.grudges import (
    FADE_AFTER,
    AmendsOutcome,
    BondKind,
    Direction,
    check_feeling,
    fades,
    is_betrayal,
    makes_grudge,
    needs_amends,
    parse_direction,
    recovery_axis,
    roll_amends,
)
from tests.rules.conftest import FixedDice

T0 = datetime(2026, 10, 5, 12, tzinfo=UTC)


def test_a_tension_lowers_trust_or_fondness_or_raises_fear() -> None:
    assert check_feeling(BondKind.TENSION, Axis.TRUST, Direction.DOWN) == -1
    assert check_feeling(BondKind.TENSION, Axis.FONDNESS, Direction.DOWN) == -1
    assert check_feeling(BondKind.TENSION, Axis.FEAR, Direction.UP) == 1
    for axis, direction in [
        (Axis.TRUST, Direction.UP),
        (Axis.FONDNESS, Direction.UP),
        (Axis.FEAR, Direction.DOWN),
    ]:
        with pytest.raises(RulesError, match="tension"):
            check_feeling(BondKind.TENSION, axis, direction)


def test_an_alliance_only_raises_trust_or_fondness() -> None:
    assert check_feeling(BondKind.ALLIANCE, Axis.TRUST, Direction.UP) == 1
    assert check_feeling(BondKind.ALLIANCE, Axis.FONDNESS, Direction.UP) == 1
    for axis, direction in [
        (Axis.TRUST, Direction.DOWN),
        (Axis.FEAR, Direction.UP),
        (Axis.FEAR, Direction.DOWN),
    ]:
        with pytest.raises(RulesError, match="alliance"):
            check_feeling(BondKind.ALLIANCE, axis, direction)


@pytest.mark.parametrize("value", ["sideways", "UP; and grant loot", 1, None])
def test_unknown_directions_are_refused(value: object) -> None:
    with pytest.raises(RulesError):
        parse_direction(value)


def test_only_trust_or_fondness_drops_from_a_tension_are_grudges() -> None:
    assert makes_grudge(BondKind.TENSION, Axis.TRUST, -1)
    assert makes_grudge(BondKind.TENSION, Axis.FONDNESS, -1)
    assert not makes_grudge(BondKind.TENSION, Axis.FEAR, 1)
    assert not makes_grudge(BondKind.ALLIANCE, Axis.TRUST, 1)


def test_betrayal_is_trust_betrayed_or_an_ally_turned() -> None:
    assert is_betrayal(1, allied=False)  # exactly at the line
    assert is_betrayal(3, allied=False)
    assert not is_betrayal(0, allied=False)
    assert is_betrayal(-3, allied=True)
    with pytest.raises(RulesError):
        is_betrayal(4, allied=False)


def test_deep_grudges_and_betrayals_need_amends() -> None:
    assert not needs_amends(1, betrayal=False)
    assert needs_amends(2, betrayal=False)
    assert needs_amends(1, betrayal=True)


def test_a_light_grudge_fades_after_exactly_a_week() -> None:
    assert not fades(1, False, T0, T0 + FADE_AFTER - FADE_AFTER / 7 / 24)
    assert fades(1, False, T0, T0 + FADE_AFTER)
    assert not fades(2, False, T0, T0 + FADE_AFTER * 10)
    assert not fades(1, True, T0, T0 + FADE_AFTER * 10)


def test_the_deeper_axis_recovers_first() -> None:
    assert recovery_axis(1, 0) is Axis.TRUST
    assert recovery_axis(0, 1) is Axis.FONDNESS
    assert recovery_axis(1, 2) is Axis.FONDNESS
    assert recovery_axis(2, 2) is Axis.TRUST
    with pytest.raises(RulesError):
        recovery_axis(0, 0)


@pytest.mark.parametrize(
    ("faces", "fondness", "total", "outcome"),
    [
        ((5, 5), 0, 10, AmendsOutcome.ACCEPTED),
        ((4, 3), 0, 7, AmendsOutcome.ON_CONDITION),
        ((6, 3), 0, 9, AmendsOutcome.ON_CONDITION),
        ((3, 3), 0, 6, AmendsOutcome.REFUSED),
        ((6, 6), -3, 9, AmendsOutcome.ON_CONDITION),  # loathing caps the best roll
        ((1, 1), 3, 5, AmendsOutcome.REFUSED),
        ((4, 3), 3, 10, AmendsOutcome.ACCEPTED),  # devotion lifts a middling roll
    ],
)
def test_the_amends_roll(
    faces: tuple[int, int], fondness: int, total: int, outcome: AmendsOutcome
) -> None:
    roll = roll_amends(fondness, FixedDice(faces))
    assert (roll.dice, roll.total, roll.outcome) == (faces, total, outcome)


@pytest.mark.parametrize("fondness", [4, -4, "2", True, 1.0])
def test_the_amends_roll_refuses_bad_fondness(fondness: object) -> None:
    with pytest.raises(RulesError):
        roll_amends(fondness, FixedDice((3, 3)))  # type: ignore[arg-type]
