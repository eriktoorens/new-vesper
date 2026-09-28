"""Bodily needs in play (D83-D89): counted on the city clock while a character is online.

Code owns every need. The DM sees them and narrates them; it never changes
them. Players ease them with /eat, /drink and /rest, and by getting out of the
weather.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from new_vesper.city.sky import season
from new_vesper.city.weather import current_weather
from new_vesper.content.loader import Content
from new_vesper.rules.needs import (
    AFFECTS,
    NEED_MAX,
    PENALTY,
    WORST_TRACK,
    Exposure,
    Need,
    NeedState,
    advance,
    exposure,
    words,
)
from new_vesper.rules.tracks import Track
from new_vesper.state import needs as stored
from new_vesper.state.characters import Character


def needs_of(content: Content, character: Character) -> frozenset[Need]:
    """The needs this character's kind of person has (D89)."""
    origin = content.origins.get(character.origin_id)
    return origin.needs if origin is not None else frozenset(Need)


def exposure_at(
    conn: sqlite3.Connection, content: Content, location_id: str | None, now: datetime
) -> Exposure:
    """Cold, hot or neither, from the place, the weather and the season (D86)."""
    if location_id is None:
        return Exposure.NONE
    place = content.locations[location_id]
    weather = current_weather(conn, content, place.region_id, now)
    current = season(content, now)
    return exposure(place.climate, weather.exposure, current.exposure if current else None)


def levels(conn: sqlite3.Connection, content: Content, character: Character) -> dict[Need, int]:
    """Each of the character's needs, by level, as last counted."""
    found = stored.get_needs(conn, character.id, sorted(needs_of(content, character)))
    return {need: state.level for need, (state, _) in found.items()}


@dataclass(frozen=True)
class Tick:
    """What the time since the last count did to the character's needs."""

    worse: dict[Need, int]  # needs that climbed, and their new level
    better: dict[Need, int]  # needs that eased
    owed: dict[Track, int]  # boxes of Harm and Fade owed for time at the worst level


def tick(conn: sqlite3.Connection, content: Content, character: Character, now: datetime) -> Tick:
    """Count the online time since the last count (D85). Offline time never counts (D88)."""
    here = exposure_at(conn, content, character.location_id, now)
    current = stored.get_needs(conn, character.id, sorted(needs_of(content, character)))
    after: dict[Need, NeedState] = {}
    worse, better, owed = {}, {}, {Track.HARM: 0, Track.FADE: 0}
    for need, (state, since) in current.items():
        seconds = 0
        if character.online and since is not None:
            seconds = max(0, int((now - since).total_seconds()))
        change = advance(need, state, seconds, here)
        after[need] = change.after
        if change.after.level > state.level:
            worse[need] = change.after.level
        elif change.after.level < state.level:
            better[need] = change.after.level
        owed[WORST_TRACK[need]] += change.worst_steps
    stored.save_needs(conn, character.id, after, now)
    return Tick(worse, better, owed)


def describe(levels_now: dict[Need, int]) -> dict[str, Any]:
    """Needs for the DM and the sheet: level, words and what they cost."""
    return {
        need.value: {
            "level": level,
            "of": NEED_MAX,
            "feels": words(need, level),
            "penalty": {s.value: -PENALTY[level] for s in AFFECTS[need]} if PENALTY[level] else {},
            "worst": level == NEED_MAX,
        }
        for need, level in sorted(levels_now.items())
    }


def summary(levels_now: dict[Need, int]) -> str:
    """One line for the player, naming only needs they can feel."""
    felt = [words(need, level) for need, level in sorted(levels_now.items()) if level > 0]
    return ", ".join(felt)
