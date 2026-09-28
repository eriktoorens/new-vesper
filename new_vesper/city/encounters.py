"""Encounters (D72-D75): code holds each district's daily pool; the DM writes each one.

The DM decides when an encounter happens and what it is, fresh every time, and
spends a slot of the right kind from today's pool. Code rolls the pool (size
and kinds, weighted by Light), generates any stranger, and logs it all.
"""

import json
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from new_vesper.budget.policy import stamp
from new_vesper.city.sky import season
from new_vesper.city.weather import current_weather
from new_vesper.content.loader import Content
from new_vesper.content.model import EncounterIdea, Spread
from new_vesper.rules import clock
from new_vesper.rules.dice import Rng
from new_vesper.rules.encounters import Kind, roll_pool
from new_vesper.rules.languages import COMMON_TONGUE
from new_vesper.rules.sky import moon, tide
from new_vesper.state import world
from new_vesper.state.events import Cause, append_event

# How far back the DM is shown the district's recent encounters, to avoid repeats.
RECENT = timedelta(days=3)
RECENT_LIMIT = 8
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

    def for_dm(self, content: Content) -> dict[str, Any]:
        return {
            "name": self.name,
            "pronouns": self.pronouns,
            "role": self.role,
            "speaks": [content.languages[self.language].name, "Registry Standard"],
        }


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


# --- the daily pool ------------------------------------------------------------


def _pool_rng(region_id: str, day: str) -> random.Random:
    """Seeded by district and city day, so the pool is the same for everyone."""
    return random.Random(f"encounters|{region_id}|{day}")


def todays_pool(
    conn: sqlite3.Connection, region_id: str, now: datetime
) -> list[tuple[int, Kind, bool, int | None]]:
    """(slot, kind, underside, spent-by) for the district's city day, rolled on first use."""
    day = clock.city_day(now)
    rows = conn.execute(
        "SELECT slot, kind, underside, encounter_id FROM encounter_pool"
        " WHERE region_id = ? AND city_day = ? ORDER BY slot",
        (region_id, day),
    ).fetchall()
    if not rows:
        light = world.get_region(conn, region_id).light
        slots = roll_pool(light, _pool_rng(region_id, day))
        conn.executemany(
            "INSERT OR IGNORE INTO encounter_pool (region_id, city_day, slot, kind, underside)"
            " VALUES (?, ?, ?, ?, ?)",
            [(region_id, day, n, s.kind.value, int(s.underside)) for n, s in enumerate(slots)],
        )
        rows = conn.execute(
            "SELECT slot, kind, underside, encounter_id FROM encounter_pool"
            " WHERE region_id = ? AND city_day = ? ORDER BY slot",
            (region_id, day),
        ).fetchall()
    return [(r[0], Kind(r[1]), bool(r[2]), r[3]) for r in rows]


def left_today(conn: sqlite3.Connection, region_id: str, now: datetime) -> dict[str, int]:
    """Unspent encounters in today's pool, by kind (underside trouble counted apart)."""
    left = {kind.value: 0 for kind in Kind} | {"underside trouble": 0}
    for _, kind, underside, spent in todays_pool(conn, region_id, now):
        if spent is None:
            left["underside trouble" if underside else kind.value] += 1
    return left


# --- ideas and variety ---------------------------------------------------------


def _fits(
    idea: EncounterIdea,
    content: Content,
    conn: sqlite3.Connection,
    location_id: str,
    now: datetime,
) -> bool:
    when = idea.when
    if when.locations and location_id not in when.locations:
        return False
    if when.parts_of_day and clock.part_of_day(now) not in when.parts_of_day:
        return False
    if when.weather or when.weather_not:
        sky = current_weather(conn, content, idea.region_id, now).id
        if (when.weather and sky not in when.weather) or sky in when.weather_not:
            return False
    if when.tide and not (when.tide & tide(now).conditions):
        return False
    current = season(content, now)
    if when.seasons and (current is None or current.id not in when.seasons):
        return False
    return not (when.moon and moon(now).phase not in when.moon)


def ideas_here(
    conn: sqlite3.Connection, content: Content, location_id: str, now: datetime
) -> list[dict[str, str]]:
    """Content ideas that would fit here and now: inspiration, never a script."""
    region_id = content.locations[location_id].region_id
    return [
        {"kind": idea.kind.value, "idea": idea.text}
        for idea in content.encounter_ideas.values()
        if idea.region_id == region_id and _fits(idea, content, conn, location_id, now)
    ]


def recent_in_district(
    conn: sqlite3.Connection, region_id: str, now: datetime
) -> list[dict[str, str]]:
    """What the DM has already written here lately, so it can do something different."""
    rows = conn.execute(
        "SELECT kind, text FROM encounters WHERE region_id = ? AND created_at >= ?"
        " AND text IS NOT NULL ORDER BY id DESC LIMIT ?",
        (region_id, stamp(now - RECENT), RECENT_LIMIT),
    )
    return [{"kind": r[0], "what_happened": r[1]} for r in rows]


# --- spending a slot -----------------------------------------------------------


class NoSuchEncounter(ValueError):
    """Today's pool has no unspent encounter of that kind."""


def spend(
    conn: sqlite3.Connection,
    content: Content,
    character_id: int,
    location_id: str,
    kind: Kind,
    text: str,
    stranger_role: str | None,
    now: datetime,
    cause: Cause,
) -> tuple[bool, Stranger | None]:
    """Use one unspent slot of this kind; returns (underside, stranger). Log it."""
    place = content.locations[location_id]
    free = [
        (slot, underside)
        for slot, k, underside, spent in todays_pool(conn, place.region_id, now)
        if k is kind and spent is None
    ]
    if not free:
        left = left_today(conn, place.region_id, now)
        raise NoSuchEncounter(f"no {kind.value} encounters left in this district today: {left}")
    slot, underside = free[0]
    day = clock.city_day(now)
    stranger = None
    if stranger_role is not None:
        # Seeded by district, day and slot: code decides who, reproducibly.
        rng = random.Random(f"stranger|{place.region_id}|{day}|{slot}")
        stranger = make_stranger(content, location_id, underside, stranger_role, rng)
    cursor = conn.execute(
        "INSERT INTO encounters (encounter_id, region_id, location_id, character_id, scene_id,"
        " kind, stranger, created_at, text, underside) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            f"{day}#{slot}",
            place.region_id,
            place.id,
            character_id,
            cause.scene_id,
            kind.value,
            None if stranger is None else json.dumps(stranger.__dict__, sort_keys=True),
            stamp(now),
            text,
            int(underside),
        ),
    )
    conn.execute(
        "UPDATE encounter_pool SET encounter_id = ? WHERE region_id = ? AND city_day = ?"
        " AND slot = ?",
        (cursor.lastrowid, place.region_id, day, slot),
    )
    append_event(
        conn,
        "encounter",
        cause,
        {
            "kind": kind.value,
            "underside": underside,
            "text": text,
            "stranger": None if stranger is None else stranger.name,
        },
        character_id=character_id,
        region_id=place.region_id,
    )
    return underside, stranger
