import random
from collections import Counter

import pytest

from new_vesper.rules.encounters import (
    KIND_PERCENT,
    Kind,
    LightBand,
    light_band,
    roll_pool,
)
from new_vesper.rules.errors import RulesError


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


def test_bad_light() -> None:
    with pytest.raises(RulesError):
        light_band(11)


def test_kind_percentages_add_up() -> None:
    assert {sum(p for _, p in table) for table in KIND_PERCENT.values()} == {100}


@pytest.mark.parametrize(("light", "low", "high"), [(8, 2, 4), (5, 3, 6), (2, 5, 9)])
def test_pool_sizes(light: int, low: int, high: int) -> None:
    rng = random.Random(3)
    sizes = {len(roll_pool(light, rng)) for _ in range(500)}
    assert sizes == set(range(low, high + 1))


def test_fallen_district_has_no_encounters() -> None:
    assert roll_pool(0, random.Random(1)) == []


def test_dark_days_hold_more_trouble_and_bleed_through() -> None:
    rng = random.Random(5)

    def share(light: int) -> tuple[float, int]:
        slots = [s for _ in range(2000) for s in roll_pool(light, rng)]
        kinds = Counter(s.kind for s in slots)
        return kinds[Kind.TROUBLE] / len(slots), sum(s.underside for s in slots)

    bright, bright_under = share(8)
    dark, dark_under = share(2)
    assert bright == pytest.approx(0.20, abs=0.03)
    assert dark == pytest.approx(0.55, abs=0.03)
    assert bright_under == 0 and dark_under > 0
