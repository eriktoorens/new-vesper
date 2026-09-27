from collections.abc import Iterable

import pytest

from new_vesper.rules.character import Sheet, create_character
from new_vesper.rules.stats import Stat


class FixedDice:
    """An RNG that returns a scripted sequence of die faces."""

    def __init__(self, faces: Iterable[int]) -> None:
        self._faces = list(faces)

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, 6)
        return self._faces.pop(0)


@pytest.fixture
def sheet() -> Sheet:
    stats = {Stat.STEEL: 2, Stat.SLICK: 1, Stat.WIRE: 1, Stat.WEIRD: 0, Stat.HEART: -1}
    return create_character(stats, ("read-the-crowd", "shrine-question"))
