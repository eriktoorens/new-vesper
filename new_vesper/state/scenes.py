"""Scenes and beats. Each region processes one beat at a time."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.state.characters import get_character
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import flag, require_row, row_id, text
from new_vesper.state.world import get_location, get_region

MAX_INTENT_LENGTH = 2000
MAX_NARRATION_LENGTH = 8000
MAX_SUMMARY_LENGTH = 2000


class HoldStance(StrEnum):
    """The default stance of a player who doesn't act in time."""

    GUARD = "guard"
    WATCH = "watch"
    WITHDRAW = "withdraw"


@dataclass(frozen=True)
class Scene:
    id: int
    region_id: str
    location_id: str | None
    shared: bool
    open: bool
    summary: str
    participants: tuple[int, ...]


@dataclass(frozen=True)
class Intent:
    character_id: int
    intent: str | None
    hold_stance: HoldStance | None


@dataclass(frozen=True)
class Beat:
    id: int
    scene_id: int
    region_id: str
    number: int
    open: bool
    narration: str
    summary: str
    intents: tuple[Intent, ...]


def get_scene(conn: sqlite3.Connection, scene_id: int) -> Scene:
    sid = row_id(scene_id, "scene id")
    row = require_row(
        conn.execute("SELECT * FROM scenes WHERE id = ?", (sid,)).fetchone(), "scene", sid
    )
    people = conn.execute(
        "SELECT character_id FROM scene_participants WHERE scene_id = ? ORDER BY character_id",
        (sid,),
    )
    return Scene(
        id=row["id"],
        region_id=row["region_id"],
        location_id=row["location_id"],
        shared=bool(row["shared"]),
        open=row["status"] == "open",
        summary=row["summary"],
        participants=tuple(p[0] for p in people),
    )


def get_beat(conn: sqlite3.Connection, beat_id: int) -> Beat:
    bid = row_id(beat_id, "beat id")
    row = require_row(
        conn.execute("SELECT * FROM beats WHERE id = ?", (bid,)).fetchone(), "beat", bid
    )
    intents = conn.execute(
        "SELECT * FROM beat_intents WHERE beat_id = ? ORDER BY created_at, character_id", (bid,)
    )
    return Beat(
        id=row["id"],
        scene_id=row["scene_id"],
        region_id=row["region_id"],
        number=row["number"],
        open=row["status"] == "open",
        narration=row["narration"],
        summary=row["summary"],
        intents=tuple(
            Intent(
                i["character_id"],
                i["intent"],
                HoldStance(i["hold_stance"]) if i["hold_stance"] else None,
            )
            for i in intents
        ),
    )


def open_scene(
    conn: sqlite3.Connection,
    region_id: str,
    cause: Cause,
    *,
    location_id: str | None = None,
    shared: bool = False,
) -> Scene:
    region = get_region(conn, region_id)
    if location_id is not None:
        location = get_location(conn, location_id)
        if location.region_id != region.id:
            raise StateError(f"location {location.id} is not in region {region.id}")
        location_id = location.id
    with atomic(conn):
        cursor = conn.execute(
            "INSERT INTO scenes (region_id, location_id, shared) VALUES (?, ?, ?)",
            (region.id, location_id, int(flag(shared, "shared"))),
        )
        scene_id = int(cursor.lastrowid or 0)
        append_event(
            conn,
            "scene_opened",
            Cause(cause.actor, cause.player_id, scene_id),
            {"location_id": location_id, "shared": shared},
            region_id=region.id,
        )
    return get_scene(conn, scene_id)


def _require_open_scene(conn: sqlite3.Connection, scene_id: int) -> Scene:
    scene = get_scene(conn, scene_id)
    if not scene.open:
        raise StateError(f"scene {scene.id} is closed")
    return scene


def join_scene(conn: sqlite3.Connection, scene_id: int, character_id: int, cause: Cause) -> Scene:
    scene = _require_open_scene(conn, scene_id)
    character = get_character(conn, character_id)
    if character.sheet.fallen:
        raise StateError("this character has fallen")
    if character.id in scene.participants:
        raise StateError(f"character {character.id} is already in scene {scene.id}")
    with atomic(conn):
        conn.execute(
            "INSERT INTO scene_participants (scene_id, character_id) VALUES (?, ?)",
            (scene.id, character.id),
        )
        append_event(
            conn,
            "scene_joined",
            Cause(cause.actor, cause.player_id, scene.id),
            character_id=character.id,
            region_id=scene.region_id,
        )
    return get_scene(conn, scene.id)


def open_beat(conn: sqlite3.Connection, scene_id: int, cause: Cause) -> Beat:
    """Open the scene's next beat. Refused while the region has another open beat."""
    with atomic(conn):
        scene = _require_open_scene(conn, scene_id)
        busy = conn.execute(
            "SELECT id FROM beats WHERE region_id = ? AND status = 'open'", (scene.region_id,)
        ).fetchone()
        if busy is not None:
            raise StateError(f"region {scene.region_id} is already processing beat {busy[0]}")
        number = conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 FROM beats WHERE scene_id = ?", (scene.id,)
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO beats (scene_id, region_id, number) VALUES (?, ?, ?)",
            (scene.id, scene.region_id, number),
        )
        beat_id = int(cursor.lastrowid or 0)
        append_event(
            conn,
            "beat_opened",
            Cause(cause.actor, cause.player_id, scene.id),
            {"beat_id": beat_id, "number": number},
            region_id=scene.region_id,
        )
    return get_beat(conn, beat_id)


def _add_intent(
    conn: sqlite3.Connection,
    beat_id: int,
    character_id: int,
    cause: Cause,
    intent: str | None,
    stance: HoldStance | None,
) -> Beat:
    with atomic(conn):
        beat = get_beat(conn, beat_id)
        if not beat.open:
            raise StateError(f"beat {beat.id} is already resolved")
        scene = get_scene(conn, beat.scene_id)
        cid = row_id(character_id, "character id")
        if cid not in scene.participants:
            raise StateError(f"character {cid} is not in scene {scene.id}")
        if any(i.character_id == cid for i in beat.intents):
            raise StateError(f"character {cid} has already acted this beat")
        conn.execute(
            "INSERT INTO beat_intents (beat_id, character_id, intent, hold_stance)"
            " VALUES (?, ?, ?, ?)",
            (beat.id, cid, intent, stance.value if stance else None),
        )
        append_event(
            conn,
            "intent_held" if stance else "intent_submitted",
            Cause(cause.actor, cause.player_id, scene.id),
            {"beat_id": beat.id, "stance": stance.value if stance else None},
            character_id=cid,
            region_id=scene.region_id,
        )
    return get_beat(conn, beat.id)


def submit_intent(
    conn: sqlite3.Connection, beat_id: int, character_id: int, intent: str, cause: Cause
) -> Beat:
    """Record what a player tries this beat. The text is untrusted and stored as data."""
    words = text(intent, "intent", MAX_INTENT_LENGTH)
    return _add_intent(conn, beat_id, character_id, cause, words, None)


def hold(
    conn: sqlite3.Connection, beat_id: int, character_id: int, stance: str, cause: Cause
) -> Beat:
    """A player who doesn't act in time keeps a default stance."""
    if not isinstance(stance, str) or stance not in {s.value for s in HoldStance}:
        raise StateError("stance must be one of guard, watch, withdraw")
    return _add_intent(conn, beat_id, character_id, cause, None, HoldStance(stance))


def resolve_beat(
    conn: sqlite3.Connection, beat_id: int, narration: str, summary: str, cause: Cause
) -> Beat:
    story = text(narration, "narration", MAX_NARRATION_LENGTH)
    short = text(summary, "summary", MAX_SUMMARY_LENGTH)
    with atomic(conn):
        beat = get_beat(conn, beat_id)
        if not beat.open:
            raise StateError(f"beat {beat.id} is already resolved")
        conn.execute(
            "UPDATE beats SET status = 'resolved', narration = ?, summary = ?,"
            " resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (story, short, beat.id),
        )
        append_event(
            conn,
            "beat_resolved",
            Cause(cause.actor, cause.player_id, beat.scene_id),
            {"beat_id": beat.id, "number": beat.number},
            region_id=beat.region_id,
        )
    return get_beat(conn, beat.id)


def recent_beats(conn: sqlite3.Connection, scene_id: int, limit: int = 3) -> list[Beat]:
    """The latest resolved beats, oldest first. Older ones live in the scene summary."""
    scene = get_scene(conn, scene_id)
    rows = conn.execute(
        "SELECT id FROM beats WHERE scene_id = ? AND status = 'resolved'"
        " ORDER BY number DESC LIMIT ?",
        (scene.id, row_id(limit, "limit")),
    ).fetchall()
    return [get_beat(conn, row[0]) for row in reversed(rows)]


def update_scene_summary(
    conn: sqlite3.Connection, scene_id: int, summary: str, cause: Cause
) -> Scene:
    """Replace the rolling summary of older beats."""
    short = text(summary, "summary", MAX_SUMMARY_LENGTH)
    scene = _require_open_scene(conn, scene_id)
    with atomic(conn):
        conn.execute("UPDATE scenes SET summary = ? WHERE id = ?", (short, scene.id))
        append_event(
            conn,
            "scene_summarized",
            Cause(cause.actor, cause.player_id, scene.id),
            region_id=scene.region_id,
        )
    return get_scene(conn, scene.id)


def close_scene(conn: sqlite3.Connection, scene_id: int, summary: str, cause: Cause) -> Scene:
    short = text(summary, "summary", MAX_SUMMARY_LENGTH)
    with atomic(conn):
        scene = _require_open_scene(conn, scene_id)
        pending = conn.execute(
            "SELECT id FROM beats WHERE scene_id = ? AND status = 'open'", (scene.id,)
        ).fetchone()
        if pending is not None:
            raise StateError(f"resolve beat {pending[0]} before closing the scene")
        conn.execute(
            "UPDATE scenes SET status = 'closed', summary = ?,"
            " closed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (short, scene.id),
        )
        append_event(
            conn,
            "scene_closed",
            Cause(cause.actor, cause.player_id, scene.id),
            region_id=scene.region_id,
        )
    return get_scene(conn, scene.id)
