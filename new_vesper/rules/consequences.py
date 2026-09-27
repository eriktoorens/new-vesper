"""Which consequences a roll's tier allows (D1, D2, D6, magic costs).

| Tier | Allowed                                                     |
| 10+  | nothing                                                     |
| 7-9  | one cost: the ordinary list, or the magic list for castings |
| 6-   | one move from the allowed list, within its magnitude cap    |
"""

from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.errors import RulesError, parse_enum, require_range
from new_vesper.rules.moves import MAGNITUDE, MoveType
from new_vesper.rules.resolver import Tier


class ConsequenceType(StrEnum):
    # The eight moves
    DEAL_HARM = "deal_harm"
    ADD_FADE = "add_fade"
    TAKE_SOMETHING = "take_something"
    SEPARATE_THEM = "separate_them"
    REVEAL_UNWELCOME_TRUTH = "reveal_unwelcome_truth"
    ADVANCE_THREAT_CLOCK = "advance_threat_clock"
    FACTION_TAKES_NOTICE = "faction_takes_notice"
    DARK_ENCROACHES = "dark_encroaches"
    # Costs that only exist on a 7-9
    NARRATIVE_COST = "narrative_cost"
    SIDE_EFFECT = "side_effect"
    FAVOR_OWED = "favor_owed"


# Ordinary 7-9 costs (D2), each at most 1.
COSTS: frozenset[ConsequenceType] = frozenset(
    {
        ConsequenceType.TAKE_SOMETHING,
        ConsequenceType.DEAL_HARM,
        ConsequenceType.ADD_FADE,
        ConsequenceType.DARK_ENCROACHES,
        ConsequenceType.NARRATIVE_COST,
    }
)
# Magic 7-9 costs: a tick of Fade, a side effect, or a favor owed to a god.
MAGIC_COSTS: frozenset[ConsequenceType] = frozenset(
    {ConsequenceType.ADD_FADE, ConsequenceType.SIDE_EFFECT, ConsequenceType.FAVOR_OWED}
)
MOVES: frozenset[ConsequenceType] = frozenset(ConsequenceType(m.value) for m in MoveType)
COST_MAGNITUDE = 1


@dataclass(frozen=True)
class Consequence:
    type: ConsequenceType
    magnitude: int


def allowed(tier: Tier, magic: bool) -> dict[ConsequenceType, int]:
    """Each allowed consequence type with its maximum magnitude."""
    if tier is Tier.CLEAN:
        return {}
    if tier is Tier.COST:
        return dict.fromkeys(sorted(MAGIC_COSTS if magic else COSTS), COST_MAGNITUDE)
    return {c: MAGNITUDE[MoveType(c.value)].high for c in sorted(MOVES)}


def validate_consequence(
    tier: Tier, magic: bool, consequence_type: object, magnitude: object
) -> Consequence:
    """Accept a consequence only if the roll's tier allows it at this magnitude."""
    parsed = parse_enum(ConsequenceType, consequence_type, "consequence type")
    limits = allowed(tier, magic)
    if not limits:
        raise RulesError("a 10+ is a clean success: no consequence is allowed")
    if parsed not in limits:
        kind = (
            "magic cost" if tier is Tier.COST and magic else "cost" if tier is Tier.COST else "move"
        )
        options = ", ".join(sorted(limits))
        raise RulesError(f"{parsed} is not an allowed {kind} for this roll; allowed: {options}")
    low = MAGNITUDE[MoveType(parsed.value)].low if parsed in MOVES else 1
    value = require_range(magnitude, f"{parsed} magnitude", low, limits[parsed])
    return Consequence(parsed, value)
