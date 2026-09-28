"""Random encounters (D67-D71): code decides whether one happens and which; the DM tells it."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from new_vesper.budget.policy import stamp
from new_vesper.city.sky import season
from new_vesper.city.weather import current_weather
from new_vesper.content.loader import Content
from new_vesper.content.model import COMMON_TONGUE, EncounterDef, Spread
from new_vesper.rules import clock
from new_vesper.rules.dice import Rng
from new_vesper.rules.encounters import Candidate, draw, encounter_happens
from new_vesper.rules.sky import moon, tide
from new_vesper.state import world
from new_vesper.state.events import Cause, append_event

# The same encounter doesn't come round again in a district for this long (D71).
COOLDOWN = timedelta(days=3)
SPREAD_WEIGHT = {Spread.MOST: 5, Spread.MANY: 4, Spread.SOME: 3, Spread.FEW: 1}
# Ordinary strangers don't speak these; Underside encounters speak Underside Cant.
NOT_FOR_STRANGERS = frozenset({"animal-speech", "underside-cant"})
PRONOUNS = (("she/her", 4), ("he/him", 4), ("they/them", 2))


@dataclass(frozen=True)
class Stranger:
    name: str
    pronouns: str
    language: str  # language id
    role: str


@dataclass(frozen=True)
class Encounter:
    id: str
    kind: str
    text: str
    stranger: Stranger | None

    def for_dm(self, content: Content) -> dict[str, Any]:
        brief: dict[str, Any] = {"kind": self.kind, "what_happens": self.text}
        if self.stranger is not None:
            brief["stranger"] = {
                "name": self.stranger.name,
                "pronouns": self.stranger.pronouns,
                "role": self.stranger.role,
                "speaks": [content.languages[self.stranger.language].name, "Registry Standard"],
            }
        return brief


def _weighted(rng: Rng, options: list[tuple[str, int]]) -> str:
    pick = rng.randint(1, sum(w for _, w in options))
    for value, weight in options:
        pick -= weight
        if pick <= 0:
            return value
    raise AssertionError("unreachable")


def make_stranger(
    content: Content, location_id: str, underside: bool, role: str, rng: Rng
) -> Stranger:
    """A one-off person whose language fits the neighborhood (D45, D70)."""
    place = content.locations[location_id]
    spread = dict(content.regions[place.region_id].languages) | dict(place.languages)
    if underside:
        language = "underside-cant"
    else:
        options = [
            (lang, SPREAD_WEIGHT[level])
            for lang, level in sorted(spread.items())
            if level in SPREAD_WEIGHT
            and lang not in NOT_FOR_STRANGERS
            and lang in content.stranger_names
        ]
        language = _weighted(rng, options) if options else COMMON_TONGUE
    names = content.stranger_names.get(language) or content.stranger_names[COMMON_TONGUE]
    name = names[rng.randint(1, len(names)) - 1]
    return Stranger(name, _weighted(rng, list(PRONOUNS)), language, role)


def _fits(
    enc: EncounterDef, content: Content, conn: sqlite3.Connection, location_id: str, now: datetime
) -> bool:
    when = enc.when
    if when.locations and location_id not in when.locations:
        return False
    if when.parts_of_day and clock.part_of_day(now) not in when.parts_of_day:
        return False
    if when.weather or when.weather_not:
        sky = current_weather(conn, content, enc.region_id, now).id
        if (when.weather and sky not in when.weather) or sky in when.weather_not:
            return False
    if when.tide and not (when.tide & tide(now).conditions):
        return False
    current = season(content, now)
    if when.seasons and (current is None or current.id not in when.seasons):
        return False
    return not (when.moon and moon(now).phase not in when.moon)


def eligible(
    conn: sqlite3.Connection, content: Content, location_id: str, now: datetime
) -> list[EncounterDef]:
    """Encounters that fit this place and moment and aren't cooling down in the district."""
    region_id = content.locations[location_id].region_id
    recent = {
        row[0]
        for row in conn.execute(
            "SELECT encounter_id FROM encounters WHERE region_id = ? AND created_at >= ?",
            (region_id, stamp(now - COOLDOWN)),
        )
    }
    return [
        enc
        for enc in content.encounters.values()
        if enc.region_id == region_id
        and enc.id not in recent
        and _fits(enc, content, conn, location_id, now)
    ]


def check_for_encounter(
    conn: sqlite3.Connection,
    content: Content,
    character_id: int,
    location_id: str,
    now: datetime,
    rng: Rng,
    cause: Cause,
) -> Encounter | None:
    """One encounter check: chance by the district's Light, then a weighted draw."""
    place = content.locations[location_id]
    light = world.get_region(conn, place.region_id).light
    if light == 0 or not encounter_happens(light, rng):
        return None
    options = eligible(conn, content, location_id, now)
    picked = draw([Candidate(e.id, e.kind, e.weight, e.underside) for e in options], light, rng)
    if picked is None:
        return None
    enc = content.encounters[picked.id]
    stranger = (
        make_stranger(content, location_id, enc.underside, enc.stranger_role, rng)
        if enc.stranger_role
        else None
    )
    conn.execute(
        "INSERT INTO encounters (encounter_id, region_id, location_id, character_id, scene_id,"
        " kind, stranger, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            enc.id,
            place.region_id,
            place.id,
            character_id,
            cause.scene_id,
            enc.kind.value,
            None if stranger is None else json.dumps(stranger.__dict__, sort_keys=True),
            stamp(now),
        ),
    )
    append_event(
        conn,
        "encounter",
        cause,
        {
            "encounter_id": enc.id,
            "kind": enc.kind.value,
            "stranger": None if stranger is None else stranger.name,
        },
        character_id=character_id,
        region_id=place.region_id,
    )
    return Encounter(enc.id, enc.kind.value, enc.text, stranger)
