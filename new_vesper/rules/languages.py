"""Languages in play (D41, D76-D81): what a character makes of speech.

Pure functions. Code decides how much of a line a character understands:
all of it in a language they speak, or what a gist roll earned them in this
scene, or nothing at all.
"""

import hashlib
import random
from enum import StrEnum

from new_vesper.rules.consequences import ConsequenceType
from new_vesper.rules.errors import RulesError
from new_vesper.rules.resolver import Tier
from new_vesper.rules.stats import Stat

# Everyone in the city speaks Registry Standard (D44).
COMMON_TONGUE = "registry-standard"
# Getting the gist of a language you don't speak is a Heart roll (D41).
GIST_STAT = Stat.HEART
# 7-9 costs that write state. Paying one buys the gist; a narrative-only cost buys
# the tone alone (D78).
REAL_COSTS: frozenset[ConsequenceType] = frozenset(
    {
        ConsequenceType.DEAL_HARM,
        ConsequenceType.ADD_FADE,
        ConsequenceType.TAKE_SOMETHING,
        ConsequenceType.DARK_ENCROACHES,
    }
)
# Gibberish is as long as the line, up to this many made-up words.
MAX_GIBBERISH_WORDS = 12


class Heard(StrEnum):
    """How much of a line the listening character understood."""

    FLUENT = "fluent"  # a language they speak: every word
    GIST = "gist"  # the gist and the tone
    TONE = "tone"  # only how it was said
    NONE = "none"  # nothing: gibberish


def check_gist_stat(stat: Stat) -> None:
    if stat is not GIST_STAT:
        raise RulesError(f"following a language you don't speak is a Heart roll, not {stat}")


def gist_heard(tier: Tier, cost_paid: ConsequenceType | None) -> Heard:
    """What a gist roll earns (D41, D78).

    10+: the gist and the tone. 7-9: the tone only, or the gist if the cost paid
    was a real one. 6 or less: nothing.
    """
    if tier is Tier.CLEAN:
        return Heard.GIST
    if tier is Tier.COST:
        return Heard.GIST if cost_paid in REAL_COSTS else Heard.TONE
    return Heard.NONE


def heard(
    language: str, spoken_by_listener: frozenset[str], earned: dict[str, Heard] | None = None
) -> Heard:
    """How much of a line in ``language`` a listener understands."""
    if language in spoken_by_listener:
        return Heard.FLUENT
    return (earned or {}).get(language, Heard.NONE)


def gibberish(words: str, sounds: tuple[str, ...], salt: str = "") -> str:
    """Made-up words standing in for a line, the same every time for the same line.

    Only for languages invented for the setting (D77); real-world tongues are
    never mocked with fake syllables.
    """
    if not sounds:
        raise RulesError("gibberish needs sounds to draw on")
    count = min(max(len(words.split()), 1), MAX_GIBBERISH_WORDS)
    seed = hashlib.sha256(f"{salt}|{words}".encode()).hexdigest()
    rng = random.Random(seed)
    made = ["".join(rng.choice(sounds) for _ in range(rng.randint(1, 2))) for _ in range(count)]
    end = words.rstrip()[-1:] if words.rstrip()[-1:] in {".", "?", "!"} else "."
    return " ".join(made).capitalize() + end
