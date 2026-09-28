"""How NPCs feel (D60, D61): three axes from -3 to +3, moving one step at a time."""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import RulesError, parse_enum, require_range

ATTITUDE_MIN = -3
ATTITUDE_MAX = 3
STEP = 1  # the most an axis moves per holder, target and scene


class Axis(StrEnum):
    TRUST = "trust"
    FONDNESS = "fondness"
    FEAR = "fear"


WORDS: dict[Axis, tuple[str, ...]] = {
    # Index 0 is -3, index 6 is +3.
    Axis.TRUST: (
        "no trust at all",
        "distrustful",
        "wary",
        "neutral",
        "inclined to trust",
        "trusting",
        "trusts completely",
    ),
    Axis.FONDNESS: ("loathing", "dislike", "cool", "indifferent", "liking", "fond", "devoted"),
    Axis.FEAR: (
        "contempt",
        "dismissive",
        "unimpressed",
        "unafraid",
        "uneasy",
        "afraid",
        "terrified",
    ),
}


@dataclass(frozen=True)
class Attitude:
    trust: int = 0
    fondness: int = 0
    fear: int = 0

    def value(self, axis: Axis) -> int:
        return getattr(self, axis.value)

    def words(self) -> dict[str, str]:
        return {axis.value: WORDS[axis][self.value(axis) - ATTITUDE_MIN] for axis in Axis}


def parse_axis(value: object) -> Axis:
    return parse_enum(Axis, value, "attitude axis")


def validate_attitude(trust: object, fondness: object, fear: object) -> Attitude:
    return Attitude(
        require_range(trust, "trust", ATTITUDE_MIN, ATTITUDE_MAX),
        require_range(fondness, "fondness", ATTITUDE_MIN, ATTITUDE_MAX),
        require_range(fear, "fear", ATTITUDE_MIN, ATTITUDE_MAX),
    )


def shift(attitude: Attitude, axis: Axis, delta: int) -> Attitude:
    """One step on one axis. Refused past the ends of the scale."""
    if delta not in (-STEP, STEP):
        raise RulesError(f"an attitude moves one step at a time, not {delta}")
    after = attitude.value(axis) + delta
    if not ATTITUDE_MIN <= after <= ATTITUDE_MAX:
        raise RulesError(
            f"{axis.value} is already at {attitude.value(axis):+d}, the end of the scale"
        )
    values = {a.value: attitude.value(a) for a in Axis} | {axis.value: after}
    return Attitude(**values)
