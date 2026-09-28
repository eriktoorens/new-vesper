"""Random encounter odds and draws (D67, D68). Pure, given an injected RNG."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import require_range
from new_vesper.rules.light import LIGHT_MAX, LIGHT_MIN

# A check happens on arrival and on every Nth beat of a scene.
CHECK_EVERY_BEATS = 5


class Kind(StrEnum):
    COLOR = "color"  # street life, no stakes
    OPPORTUNITY = "opportunity"  # something to gain or learn
    TROUBLE = "trouble"  # something that may call for a roll


class LightBand(StrEnum):
    BRIGHT = "bright"  # 7-10
    DIMMING = "dimming"  # 4-6
    DARK = "dark"  # 1-3 (0 has fallen into Old Vesper)


CHANCE_PERCENT = {LightBand.BRIGHT: 20, LightBand.DIMMING: 30, LightBand.DARK: 45}
# As Light falls, trouble and Underside bleed-through grow more likely.
TROUBLE_WEIGHT = {LightBand.BRIGHT: 1, LightBand.DIMMING: 2, LightBand.DARK: 3}
UNDERSIDE_WEIGHT = {LightBand.BRIGHT: 1, LightBand.DIMMING: 2, LightBand.DARK: 4}


@dataclass(frozen=True)
class Candidate:
    id: str
    kind: Kind
    weight: int
    underside: bool


def light_band(light: int) -> LightBand:
    value = require_range(light, "region light", LIGHT_MIN, LIGHT_MAX)
    if value >= 7:
        return LightBand.BRIGHT
    if value >= 4:
        return LightBand.DIMMING
    return LightBand.DARK


def encounter_happens(light: int, rng: Rng) -> bool:
    """One check: a d100 at or under the band's chance."""
    return rng.randint(1, 100) <= CHANCE_PERCENT[light_band(light)]


def effective_weight(candidate: Candidate, band: LightBand) -> int:
    weight = candidate.weight
    if candidate.kind is Kind.TROUBLE:
        weight *= TROUBLE_WEIGHT[band]
    if candidate.underside:
        weight *= UNDERSIDE_WEIGHT[band]
    return weight


def draw(candidates: Sequence[Candidate], light: int, rng: Rng) -> Candidate | None:
    """Pick one eligible encounter, weighted for the district's Light."""
    band = light_band(light)
    weights = [effective_weight(c, band) for c in candidates]
    total = sum(weights)
    if total == 0:
        return None
    pick = rng.randint(1, total)
    for candidate, weight in zip(candidates, weights, strict=True):
        pick -= weight
        if pick <= 0:
            return candidate
    raise AssertionError("unreachable: pick exceeded total weight")


def is_check_beat(beat_number: int) -> bool:
    return beat_number > 1 and beat_number % CHECK_EVERY_BEATS == 0
