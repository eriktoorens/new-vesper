"""World data: origins, knacks, regions and locations."""

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass

from new_vesper.rules.errors import require_range
from new_vesper.rules.light import LIGHT_MAX, LIGHT_MIN, LightChange
from new_vesper.rules.stats import Stat, parse_stat
from new_vesper.state.db import atomic
from new_vesper.state.errors import StaleStateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import as_state_error, flag, require_row, slug, text


@dataclass(frozen=True)
class Origin:
    id: str
    name: str
    trait: str
    tags: frozenset[str]


@dataclass(frozen=True)
class Knack:
    id: str
    name: str
    stat: Stat
    trigger_text: str
    clean_effect: str
    cost_effect: str
    limits: str
    roll_bonus: int
    advanced: bool
    approved: bool
    tags: frozenset[str]


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    light: int

    @property
    def fallen(self) -> bool:
        return self.light == LIGHT_MIN


@dataclass(frozen=True)
class Location:
    id: str
    region_id: str
    name: str
    is_haven: bool


def _tags(values: Iterable[str]) -> list[str]:
    return sorted({slug(tag, "tag") for tag in values})


def add_origin(
    conn: sqlite3.Connection,
    origin_id: str,
    name: str,
    trait: str,
    tags: Iterable[str],
    cause: Cause,
) -> Origin:
    oid = slug(origin_id, "origin id")
    tag_list = _tags(tags)
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO origins (id, name, trait) VALUES (?, ?, ?)",
            (oid, text(name, "origin name", 80), text(trait, "origin trait", 300)),
        )
        conn.executemany(
            "INSERT INTO origin_tags (origin_id, tag) VALUES (?, ?)", [(oid, t) for t in tag_list]
        )
        append_event(conn, "origin_added", cause, {"origin_id": oid, "tags": tag_list})
    return get_origin(conn, oid)


def get_origin(conn: sqlite3.Connection, origin_id: str) -> Origin:
    row = require_row(
        conn.execute("SELECT * FROM origins WHERE id = ?", (origin_id,)).fetchone(),
        "origin",
        origin_id,
    )
    tags = conn.execute("SELECT tag FROM origin_tags WHERE origin_id = ?", (origin_id,))
    return Origin(row["id"], row["name"], row["trait"], frozenset(t[0] for t in tags))


def add_knack(
    conn: sqlite3.Connection,
    knack_id: str,
    name: str,
    stat: Stat | str,
    trigger_text: str,
    clean_effect: str,
    cost_effect: str,
    cause: Cause,
    *,
    limits: str = "",
    roll_bonus: int = 0,
    advanced: bool = False,
    approved: bool = False,
    tags: Iterable[str] = (),
) -> Knack:
    """Add a knack to the shared catalog. Player-proposed knacks start unapproved."""
    kid = slug(knack_id, "knack id")
    tag_list = _tags(tags)
    with as_state_error():
        parsed_stat = parse_stat(stat)
        require_range(roll_bonus, "roll bonus", 0, 1)
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO knacks (id, name, stat, trigger_text, clean_effect, cost_effect,"
            " limits, roll_bonus, advanced, approved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kid,
                text(name, "knack name", 80),
                parsed_stat.value,
                text(trigger_text, "knack trigger", 500),
                text(clean_effect, "10+ effect", 500),
                text(cost_effect, "7-9 effect", 500),
                text(limits, "knack limits", 300, allow_empty=True),
                roll_bonus,
                int(flag(advanced, "advanced")),
                int(flag(approved, "approved")),
            ),
        )
        conn.executemany(
            "INSERT INTO knack_tags (knack_id, tag) VALUES (?, ?)", [(kid, t) for t in tag_list]
        )
        append_event(conn, "knack_added", cause, {"knack_id": kid, "approved": approved})
    return get_knack(conn, kid)


def approve_knack(conn: sqlite3.Connection, knack_id: str, cause: Cause) -> Knack:
    knack = get_knack(conn, knack_id)
    with atomic(conn):
        conn.execute("UPDATE knacks SET approved = 1 WHERE id = ?", (knack.id,))
        append_event(conn, "knack_approved", cause, {"knack_id": knack.id})
    return get_knack(conn, knack.id)


def get_knack(conn: sqlite3.Connection, knack_id: str) -> Knack:
    row = require_row(
        conn.execute("SELECT * FROM knacks WHERE id = ?", (knack_id,)).fetchone(),
        "knack",
        knack_id,
    )
    tags = conn.execute("SELECT tag FROM knack_tags WHERE knack_id = ?", (knack_id,))
    return Knack(
        id=row["id"],
        name=row["name"],
        stat=Stat(row["stat"]),
        trigger_text=row["trigger_text"],
        clean_effect=row["clean_effect"],
        cost_effect=row["cost_effect"],
        limits=row["limits"],
        roll_bonus=row["roll_bonus"],
        advanced=bool(row["advanced"]),
        approved=bool(row["approved"]),
        tags=frozenset(t[0] for t in tags),
    )


def add_region(
    conn: sqlite3.Connection, region_id: str, name: str, light: int, cause: Cause
) -> Region:
    rid = slug(region_id, "region id")
    with as_state_error():
        require_range(light, "region light", LIGHT_MIN, LIGHT_MAX)
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO regions (id, name, light) VALUES (?, ?, ?)",
            (rid, text(name, "region name", 80), light),
        )
        append_event(conn, "region_added", cause, {"light": light}, region_id=rid)
    return get_region(conn, rid)


def get_region(conn: sqlite3.Connection, region_id: str) -> Region:
    row = require_row(
        conn.execute("SELECT * FROM regions WHERE id = ?", (region_id,)).fetchone(),
        "region",
        region_id,
    )
    return Region(row["id"], row["name"], row["light"])


def apply_light_change(
    conn: sqlite3.Connection, region_id: str, change: LightChange, cause: Cause, reason: str
) -> Region:
    """Write a Light change computed by the rules engine.

    ``change.before`` must match the stored Light, so two players moving the
    same region at once cannot silently overwrite each other.
    """
    why = text(reason, "reason", 300)
    with atomic(conn):
        region = get_region(conn, region_id)
        if region.light != change.before:
            raise StaleStateError(
                f"region {region.id} Light is {region.light}, not {change.before}"
            )
        with as_state_error():
            require_range(change.after, "region light", LIGHT_MIN, LIGHT_MAX)
        conn.execute("UPDATE regions SET light = ? WHERE id = ?", (change.after, region.id))
        append_event(
            conn,
            "light_changed",
            cause,
            {"before": change.before, "after": change.after, "fell": change.fell, "reason": why},
            region_id=region.id,
        )
    return get_region(conn, region.id)


def add_location(
    conn: sqlite3.Connection,
    location_id: str,
    region_id: str,
    name: str,
    cause: Cause,
    *,
    is_haven: bool = False,
) -> Location:
    lid = slug(location_id, "location id")
    region = get_region(conn, region_id)
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO locations (id, region_id, name, is_haven) VALUES (?, ?, ?, ?)",
            (lid, region.id, text(name, "location name", 80), int(flag(is_haven, "is_haven"))),
        )
        append_event(conn, "location_added", cause, {"location_id": lid}, region_id=region.id)
    return get_location(conn, lid)


def get_location(conn: sqlite3.Connection, location_id: str) -> Location:
    row = require_row(
        conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone(),
        "location",
        location_id,
    )
    return Location(row["id"], row["region_id"], row["name"], bool(row["is_haven"]))
