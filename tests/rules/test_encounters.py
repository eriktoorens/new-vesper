import random

import pytest

from new_vesper.rules.encounters import (
    Candidate,
    Kind,
    LightBand,
    draw,
    effective_weight,
    encounter_happens,
    is_check_beat,
    light_band,
)
from new_vesper.rules.errors import RulesError
from tests.dm.conftest import SeqRng


class D100:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, 100)
        return self.value


@pytest.mark.parametrize(
    ("light", "band"),
    [
        (10, LightBand.BRIGHT),
        (7, LightBand.BRIGHT),
        (6, LightBand.DIMMING),
        (4, LightBand.DIMMING),
        (3, LightBand.DARK),
        (1, LightBand.DARK),
    ],
)
def test_bands(light: int, band: LightBand) -> None:
    assert light_band(light) is band


@pytest.mark.parametrize(("light", "edge"), [(8, 20), (5, 30), (2, 45)])
def test_chance_edges(light: int, edge: int) -> None:
    assert encounter_happens(light, D100(edge))
    assert not encounter_happens(light, D100(edge + 1))


def test_bad_light() -> None:
    with pytest.raises(RulesError):
        light_band(11)


def test_trouble_and_underside_grow_as_light_falls() -> None:
    trouble = Candidate("t", Kind.TROUBLE, 2, False)
    bleed = Candidate("u", Kind.TROUBLE, 1, True)
    color = Candidate("c", Kind.COLOR, 3, False)
    assert [effective_weight(trouble, b) for b in LightBand] == [2, 4, 6]
    assert [effective_weight(bleed, b) for b in LightBand] == [1, 4, 12]
    assert {effective_weight(color, b) for b in LightBand} == {3}


def test_draw_boundaries_and_empty() -> None:
    options = [Candidate("a", Kind.COLOR, 1, False), Candidate("b", Kind.TROUBLE, 1, False)]
    assert draw(options, 8, SeqRng(1)).id == "a"
    assert draw(options, 8, SeqRng(2)).id == "b"
    assert draw([], 8, SeqRng()) is None


def test_dark_districts_draw_more_trouble() -> None:
    options = [Candidate("c", Kind.COLOR, 3, False), Candidate("t", Kind.TROUBLE, 1, False)]
    rng = random.Random(9)

    def share(light: int) -> float:
        return sum(draw(options, light, rng).id == "t" for _ in range(4000)) / 4000

    assert share(2) > share(8) + 0.25


def test_check_beats() -> None:
    assert [n for n in range(1, 16) if is_check_beat(n)] == [5, 10, 15]
