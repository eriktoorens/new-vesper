"""Harm and Fade: two six-box tracks.

| Boxes | Harm                               | Fade                     |
| 1-2   | Bruised                            | Unnoticed                |
| 3-4   | Wounded: -1 to Steel and Slick     | Unseen                   |
| 5-6   | Critical; at 6, Fall or Endure     | Slipping; at 6, into Old Vesper |
"""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import parse_enum, require_int, require_range
from new_vesper.rules.stats import Stat

TRACK_MAX = 6
# A bad hit deals 1-3 boxes.
BAD_HIT_MAX = 3

WOUNDED_FROM = 3
CRITICAL_FROM = 5
WOUNDED_PENALTY = 1
WOUNDED_STATS: frozenset[Stat] = frozenset({Stat.STEEL, Stat.SLICK})


class Track(StrEnum):
    HARM = "harm"
    FADE = "fade"


class HarmStatus(StrEnum):
    UNHURT = "unhurt"
    BRUISED = "bruised"
    WOUNDED = "wounded"
    CRITICAL = "critical"


class FadeStatus(StrEnum):
    SEEN = "seen"
    UNNOTICED = "unnoticed"
    UNSEEN = "unseen"
    SLIPPING = "slipping"


class FullHarmChoice(StrEnum):
    FALL = "fall"  # die performing a final act that permanently changes the world
    ENDURE = "endure"  # survive with a permanent scar or condition


@dataclass(frozen=True)
class TrackChange:
    track: Track
    before: int
    after: int
    filled: bool  # this change brought the track to its maximum


def parse_full_harm_choice(value: object) -> FullHarmChoice:
    return parse_enum(FullHarmChoice, value, "full harm choice")


def _band(value: int) -> int:
    """0 for an empty track, then 1, 2, 3 for boxes 1-2, 3-4, 5-6."""
    return (require_range(value, "track value", 0, TRACK_MAX) + 1) // 2


def harm_status(harm: int) -> HarmStatus:
    return list(HarmStatus)[_band(harm)]


def fade_status(fade: int) -> FadeStatus:
    return list(FadeStatus)[_band(fade)]


def change_track(track: Track, current: int, delta: int) -> TrackChange:
    """Add ``delta`` boxes (negative to recover), clamped to 0..TRACK_MAX."""
    require_range(current, f"current {track}", 0, TRACK_MAX)
    require_int(delta, f"{track} change")
    after = min(TRACK_MAX, max(0, current + delta))
    return TrackChange(
        track=track,
        before=current,
        after=after,
        filled=after == TRACK_MAX and current < TRACK_MAX,
    )


def must_fall_or_endure(harm: int) -> bool:
    """At 6 Harm the player chooses Fall or Endure. Dice never kill."""
    return require_range(harm, "harm", 0, TRACK_MAX) == TRACK_MAX


def slips_into_old_vesper(fade: int) -> bool:
    """At 6 Fade the character slips into Old Vesper. Changed, not dead."""
    return require_range(fade, "fade", 0, TRACK_MAX) == TRACK_MAX


def is_wounded(harm: int) -> bool:
    """Wounded from 3 boxes. The penalty carries into Critical (5-6).

    The design doc lists the -1 only on the 3-4 row; this reads Critical as
    at least as bad as Wounded. Flagged for confirmation in docs/design.md.
    """
    return require_range(harm, "harm", 0, TRACK_MAX) >= WOUNDED_FROM


def effective_stat(stat: Stat, base: int, harm: int) -> int:
    """The stat as rolled, after the Wounded penalty."""
    require_int(base, f"{stat} value")
    if stat in WOUNDED_STATS and is_wounded(harm):
        return base - WOUNDED_PENALTY
    return base
