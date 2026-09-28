"""The eight moves the DM may make on a 6 or less, with magnitude caps."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import parse_enum, require_range
from new_vesper.rules.tracks import BAD_HIT_MAX


class MoveType(StrEnum):
    DEAL_HARM = "deal_harm"
    ADD_FADE = "add_fade"
    TAKE_SOMETHING = "take_something"
    SEPARATE_THEM = "separate_them"
    REVEAL_UNWELCOME_TRUTH = "reveal_unwelcome_truth"
    ADVANCE_THREAT_CLOCK = "advance_threat_clock"
    FACTION_TAKES_NOTICE = "faction_takes_notice"
    DARK_ENCROACHES = "dark_encroaches"


@dataclass(frozen=True)
class MagnitudeRange:
    low: int
    high: int


# Harm and Fade: a bad hit deals 1-3 boxes. The dark encroaches is exactly
# region Light -1. The remaining moves happen once per move; magnitude 1 is
# the only legal value until the design doc says otherwise.
MAGNITUDE: dict[MoveType, MagnitudeRange] = {
    MoveType.DEAL_HARM: MagnitudeRange(1, BAD_HIT_MAX),
    MoveType.ADD_FADE: MagnitudeRange(1, BAD_HIT_MAX),
    MoveType.TAKE_SOMETHING: MagnitudeRange(1, 1),
    MoveType.SEPARATE_THEM: MagnitudeRange(1, 1),
    MoveType.REVEAL_UNWELCOME_TRUTH: MagnitudeRange(1, 1),
    MoveType.ADVANCE_THREAT_CLOCK: MagnitudeRange(1, 1),
    MoveType.FACTION_TAKES_NOTICE: MagnitudeRange(1, 1),
    MoveType.DARK_ENCROACHES: MagnitudeRange(1, 1),
}

# Moves that write a character's track. Offline characters cannot be harmed
# and their tracks don't change.
TRACK_MOVES: frozenset[MoveType] = frozenset({MoveType.DEAL_HARM, MoveType.ADD_FADE})


@dataclass(frozen=True)
class Move:
    type: MoveType
    magnitude: int


def parse_move_type(value: object) -> MoveType:
    return parse_enum(MoveType, value, "move type")


def validate_move(move_type: object, magnitude: object) -> Move:
    """Accept a move only if its type is allowed and its magnitude is in range.

    Out-of-range magnitudes are rejected, not clamped, so the model sees the
    error instead of a silently different outcome.
    """
    parsed = parse_move_type(move_type)
    limits = MAGNITUDE[parsed]
    value = require_range(magnitude, f"{parsed} magnitude", limits.low, limits.high)
    return Move(type=parsed, magnitude=value)
