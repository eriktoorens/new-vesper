"""The daily encounter pool (D72, D74): how many encounters a district holds, and of what kind.

The DM writes every encounter and decides when it happens (D73); code decides how
many a district's day holds and their kinds, weighted by its Light. Pure, given
an injected RNG.
"""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import require_range
from new_vesper.rules.light import LIGHT_MAX, LIGHT_MIN


class Kind(StrEnum):
    COLOR = "color"  # street life, no stakes
    OPPORTUNITY = "opportunity"  # something to gain or learn
    TROUBLE = "trouble"  # something that may call for a roll


class LightBand(StrEnum):
    BRIGHT = "bright"  # 7-10
    DIMMING = "dimming"  # 4-6
    DARK = "dark"  # 1-3 (0 has fallen into Old Vesper)


# Pool size: (number of dice, sides, bonus). Bright 2-4, dimming 3-6, dark 5-9.
POOL_DICE = {LightBand.BRIGHT: (1, 3, 1), LightBand.DIMMING: (1, 4, 2), LightBand.DARK: (2, 3, 3)}
# Percent chance of each kind per slot, by band.
KIND_PERCENT = {
    LightBand.BRIGHT: ((Kind.COLOR, 50), (Kind.OPPORTUNITY, 30), (Kind.TROUBLE, 20)),
    LightBand.DIMMING: ((Kind.COLOR, 35), (Kind.OPPORTUNITY, 30), (Kind.TROUBLE, 35)),
    LightBand.DARK: ((Kind.COLOR, 20), (Kind.OPPORTUNITY, 25), (Kind.TROUBLE, 55)),
}
# In a dark district, this percent of trouble is Old Vesper bleeding through.
UNDERSIDE_PERCENT = {LightBand.BRIGHT: 0, LightBand.DIMMING: 0, LightBand.DARK: 50}


@dataclass(frozen=True)
class Slot:
    kind: Kind
    underside: bool = False


def light_band(light: int) -> LightBand:
    value = require_range(light, "region light", LIGHT_MIN, LIGHT_MAX)
    if value >= 7:
        return LightBand.BRIGHT
    if value >= 4:
        return LightBand.DIMMING
    return LightBand.DARK


def roll_pool(light: int, rng: Rng) -> list[Slot]:
    """A district's encounters for one day. A fallen district (Light 0) has none."""
    if require_range(light, "region light", LIGHT_MIN, LIGHT_MAX) == LIGHT_MIN:
        return []
    band = light_band(light)
    count, sides, bonus = POOL_DICE[band]
    size = sum(rng.randint(1, sides) for _ in range(count)) + bonus
    slots = []
    for _ in range(size):
        kind = _pick_kind(band, rng.randint(1, 100))
        underside = kind is Kind.TROUBLE and rng.randint(1, 100) <= UNDERSIDE_PERCENT[band]
        slots.append(Slot(kind, underside))
    return slots


def _pick_kind(band: LightBand, d100: int) -> Kind:
    for kind, percent in KIND_PERCENT[band]:
        d100 -= percent
        if d100 <= 0:
            return kind
    raise AssertionError("kind percentages must add up to 100")
