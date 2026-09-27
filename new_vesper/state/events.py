"""The append-only event log."""

import json
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Actor(StrEnum):
    DM = "dm"
    PLAYER = "player"
    SYSTEM = "system"


@dataclass(frozen=True)
class Cause:
    """Who caused a write, and in which scene. Attached to its event."""

    actor: Actor
    player_id: int | None = None
    scene_id: int | None = None


SYSTEM = Cause(Actor.SYSTEM)


@dataclass(frozen=True)
class Event:
    id: int
    kind: str
    actor: Actor
    player_id: int | None
    character_id: int | None
    region_id: str | None
    scene_id: int | None
    payload: dict[str, Any]
    created_at: str


def append_event(
    conn: sqlite3.Connection,
    kind: str,
    cause: Cause,
    payload: dict[str, Any] | None = None,
    *,
    character_id: int | None = None,
    region_id: str | None = None,
) -> int:
    """Append one event. Called by repository writes inside their transaction."""
    cursor = conn.execute(
        "INSERT INTO events (kind, actor, player_id, character_id, region_id, scene_id, payload)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            kind,
            Actor(cause.actor).value,
            cause.player_id,
            character_id,
            region_id,
            cause.scene_id,
            json.dumps(payload or {}, sort_keys=True),
        ),
    )
    return int(cursor.lastrowid or 0)


def _event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        kind=row["kind"],
        actor=Actor(row["actor"]),
        player_id=row["player_id"],
        character_id=row["character_id"],
        region_id=row["region_id"],
        scene_id=row["scene_id"],
        payload=json.loads(row["payload"]),
        created_at=row["created_at"],
    )


def list_events(
    conn: sqlite3.Connection,
    *,
    character_id: int | None = None,
    region_id: str | None = None,
    scene_id: int | None = None,
    kind: str | None = None,
    after_id: int = 0,
    limit: int = 100,
) -> list[Event]:
    """Events in order, optionally filtered by character, region, scene or kind."""
    clauses: list[str] = ["id > ?"]
    params: list[object] = [after_id]
    if scene_id is not None:
        clauses.append("scene_id = ?")
        params.append(scene_id)
    if kind is not None:
        clauses.append("kind = ?")
        params.append(kind)
    if character_id is not None:
        clauses.append("character_id = ?")
        params.append(character_id)
    if region_id is not None:
        clauses.append("region_id = ?")
        params.append(region_id)
    rows = conn.execute(
        f"SELECT * FROM events WHERE {' AND '.join(clauses)} ORDER BY id LIMIT ?",
        (*params, limit),
    )
    return [_event(row) for row in rows]
