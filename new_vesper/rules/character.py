"""The mechanical character sheet: creation, tracks and the Fall-or-Endure choice.

Narrative parts of a character (origin trait, Bond, names) live in state and
content; this sheet holds only what the rules act on.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace

from new_vesper.rules.errors import RulesError
from new_vesper.rules.stats import Stat, validate_starting_stats
from new_vesper.rules.tracks import (
    ENDURE_HARM,
    FullHarmChoice,
    Track,
    TrackChange,
    change_track,
    effective_stat,
    must_fall_or_endure,
    parse_full_harm_choice,
)

STARTING_LEVEL = 1
STARTING_KNACKS = 2

_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


NAME_MAX = 40
PRONOUNS_MAX = 30
# Letters in any script, digits, and the punctuation names use: spaces, apostrophes,
# hyphens and periods (O'Neil, Okoye-Lim, H. Okoye). No slashes, symbols or code.
_NAME_PUNCTUATION = frozenset(" '\u2019-.")
# One or more words joined by slashes: she/her, it/its, they/them, xe/xem, any.
_PRONOUNS = re.compile(r"[^\W\d_]+(?:\s*/\s*[^\W\d_]+)*")


def validate_name(value: object) -> str:
    """A character's name: 1-40 characters of letters, digits and name punctuation (D107)."""
    if not isinstance(value, str):
        raise RulesError("a name must be text")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise RulesError("a name is one line, with no control characters")
    name = " ".join(value.split())
    if not name or len(name) > NAME_MAX:
        raise RulesError(f"a name is 1 to {NAME_MAX} characters")
    if not any(c.isalpha() for c in name):
        raise RulesError("a name needs at least one letter")
    if any(not (c.isalnum() or c in _NAME_PUNCTUATION) for c in name):
        raise RulesError("a name uses letters, digits, spaces, apostrophes, hyphens and periods")
    return name


def validate_pronouns(value: object) -> str:
    """Pronouns as words joined by slashes, such as she/her or it/its (D107)."""
    if not isinstance(value, str):
        raise RulesError("pronouns must be text")
    pronouns = value.strip()
    if len(pronouns) > PRONOUNS_MAX or not _PRONOUNS.fullmatch(pronouns):
        raise RulesError("write pronouns as words joined by slashes, like she/her or they/them")
    return pronouns


def validate_id(value: object, name: str) -> str:
    """Knack, scar and evolution ids are short slugs; free text is rejected."""
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise RulesError(f"{name} must be a lowercase slug of 1-64 characters")
    return value


@dataclass(frozen=True)
class Sheet:
    stats: Mapping[Stat, int]
    knacks: tuple[str, ...]
    level: int = STARTING_LEVEL
    xp: int = 0
    harm: int = 0
    fade: int = 0
    scars: tuple[str, ...] = ()
    advanced_knacks: tuple[str, ...] = ()
    origin_evolutions: tuple[str, ...] = ()
    # The one stat an advanced knack has let reach +4, if any.
    boosted_stat: Stat | None = None
    fallen: bool = False
    slipped: bool = False  # slipped into Old Vesper: an Underside character now

    def roll_stat(self, stat: Stat) -> int:
        """The value to roll with, after the Wounded penalty."""
        return effective_stat(stat, self.stats[stat], self.harm)


def create_character(stats: Mapping[Stat, int], knacks: tuple[str, ...]) -> Sheet:
    """Assign the starting array and pick two knacks."""
    checked = validate_starting_stats(stats)
    if not isinstance(knacks, tuple) or len(knacks) != STARTING_KNACKS:
        raise RulesError(f"a new character picks exactly {STARTING_KNACKS} knacks")
    ids = tuple(validate_id(knack, "knack") for knack in knacks)
    if len(set(ids)) != len(ids):
        raise RulesError("starting knacks must be different")
    return Sheet(stats=checked, knacks=ids)


def _require_active(sheet: Sheet) -> None:
    if sheet.fallen:
        raise RulesError("this character has fallen")


def apply_track(sheet: Sheet, track: Track, delta: int) -> tuple[Sheet, TrackChange]:
    """Change Harm or Fade. Filling Fade slips the character into Old Vesper.

    Filling Harm never kills: it leaves the character awaiting Fall or Endure.
    """
    _require_active(sheet)
    if track is Track.HARM:
        change = change_track(track, sheet.harm, delta)
        return replace(sheet, harm=change.after), change
    change = change_track(track, sheet.fade, delta)
    return replace(sheet, fade=change.after, slipped=sheet.slipped or change.filled), change


def resolve_full_harm(sheet: Sheet, choice: object, scar: object = None) -> Sheet:
    """At full Harm the player chooses. Fall ends the character; Endure scars them.

    After Endure, Harm drops to 4: still Wounded (D13).
    """
    _require_active(sheet)
    if not must_fall_or_endure(sheet.harm):
        raise RulesError("Fall or Endure is chosen only at full Harm")
    parsed = parse_full_harm_choice(choice)
    if parsed is FullHarmChoice.FALL:
        if scar is not None:
            raise RulesError("a character who falls takes no scar")
        return replace(sheet, fallen=True)
    scar_id = validate_id(scar, "scar")
    if scar_id in sheet.scars:
        raise RulesError(f"already carries scar {scar_id!r}")
    return replace(sheet, scars=(*sheet.scars, scar_id), harm=ENDURE_HARM)
