"""NPC attitudes, the reasons behind every change, and NPC memories."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.attitudes import Attitude, Axis, shift
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import as_state_error, row_id, slug, text

MAX_REASON = 300
NEUTRAL = Attitude()
MAX_NOTE = 300
MAX_SUMMARY = 600


class TargetKind(StrEnum):
    CHARACTER = "character"
    NPC = "npc"


@dataclass(frozen=True)
class Change:
    axis: Axis
    before: int
    after: int
    reason: str
    created_at: str


def _key(holder: str, kind: TargetKind, target: str | int) -> tuple[str, str, str]:
    holder_id = slug(holder, "npc id")
    if kind is TargetKind.CHARACTER:
        return holder_id, kind.value, str(row_id(target, "character id"))
    target_id = slug(target, "npc id")
    if target_id == holder_id:
        raise StateError("an NPC has no attitude toward themselves")
    return holder_id, kind.value, target_id


def get_attitude(
    conn: sqlite3.Connection,
    holder: str,
    kind: TargetKind,
    target: str | int,
    default: Attitude = NEUTRAL,
) -> Attitude:
    """The stored attitude, or ``default`` if the NPC has never shifted on this target."""
    row = conn.execute(
        "SELECT trust, fondness, fear FROM attitudes"
        " WHERE holder_npc = ? AND target_kind = ? AND target_id = ?",
        _key(holder, kind, target),
    ).fetchone()
    return default if row is None else Attitude(*row)


def set_attitude(
    conn: sqlite3.Connection,
    holder: str,
    kind: TargetKind,
    target: str | int,
    attitude: Attitude,
) -> None:
    """Store an attitude outright: for seeding the authored NPC web from content."""
    with as_state_error():
        conn.execute(
            "INSERT INTO attitudes (holder_npc, target_kind, target_id, trust, fondness, fear)"
            " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET trust = excluded.trust,"
            " fondness = excluded.fondness, fear = excluded.fear",
            (*_key(holder, kind, target), attitude.trust, attitude.fondness, attitude.fear),
        )


def changed_this_scene(
    conn: sqlite3.Connection,
    holder: str,
    kind: TargetKind,
    target: str | int,
    axis: Axis,
    scene_id: int,
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM attitude_changes WHERE holder_npc = ? AND target_kind = ?"
        " AND target_id = ? AND axis = ? AND scene_id = ?",
        (*_key(holder, kind, target), axis.value, scene_id),
    ).fetchone()
    return row is not None


def change_attitude(
    conn: sqlite3.Connection,
    holder: str,
    kind: TargetKind,
    target: str | int,
    axis: Axis,
    delta: int,
    reason: str,
    cause: Cause,
    *,
    default: Attitude = NEUTRAL,
) -> Attitude:
    """Move one axis one step, recording why (D61). Once per axis per scene."""
    key = _key(holder, kind, target)
    why = text(reason, "reason", MAX_REASON).strip()
    scene_id = cause.scene_id
    if scene_id is not None and changed_this_scene(conn, holder, kind, target, axis, scene_id):
        raise StateError(f"{axis.value} already moved this scene; attitudes change slowly")
    with atomic(conn):
        before = get_attitude(conn, holder, kind, target, default)
        with as_state_error():
            after = shift(before, axis, delta)
        set_attitude(conn, holder, kind, target, after)
        conn.execute(
            "INSERT INTO attitude_changes (holder_npc, target_kind, target_id, axis, before,"
            " after, reason, scene_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*key, axis.value, before.value(axis), after.value(axis), why, scene_id),
        )
        append_event(
            conn,
            "attitude_changed",
            cause,
            {
                "npc_id": key[0],
                "target_kind": key[1],
                "target_id": key[2],
                "axis": axis.value,
                "before": before.value(axis),
                "after": after.value(axis),
                "reason": why,
            },
            character_id=int(key[2]) if kind is TargetKind.CHARACTER else None,
        )
    return after


def recent_changes(
    conn: sqlite3.Connection, holder: str, kind: TargetKind, target: str | int, limit: int = 5
) -> list[Change]:
    """The latest changes and their reasons, newest first."""
    rows = conn.execute(
        "SELECT axis, before, after, reason, created_at FROM attitude_changes"
        " WHERE holder_npc = ? AND target_kind = ? AND target_id = ? ORDER BY id DESC LIMIT ?",
        (*_key(holder, kind, target), limit),
    )
    return [Change(Axis(r[0]), r[1], r[2], r[3], r[4]) for r in rows]


# --- memories ------------------------------------------------------------------


def add_memory(
    conn: sqlite3.Connection, npc_id: str, character_id: int, note: str, cause: Cause
) -> None:
    line = text(note, "memory", MAX_NOTE).strip()
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO npc_memories (npc_id, character_id, scene_id, note) VALUES (?, ?, ?, ?)",
            (slug(npc_id, "npc id"), row_id(character_id, "character id"), cause.scene_id, line),
        )
        append_event(conn, "npc_remembered", cause, {"npc_id": npc_id}, character_id=character_id)


@dataclass(frozen=True)
class Memory:
    summary: str | None
    notes: tuple[str, ...]  # oldest first, not yet folded


def memory_of(conn: sqlite3.Connection, npc_id: str, character_id: int) -> Memory:
    summary = conn.execute(
        "SELECT summary FROM npc_memory_summaries WHERE npc_id = ? AND character_id = ?",
        (npc_id, character_id),
    ).fetchone()
    notes = conn.execute(
        "SELECT note FROM npc_memories WHERE npc_id = ? AND character_id = ? AND folded = 0"
        " ORDER BY id",
        (npc_id, character_id),
    ).fetchall()
    return Memory(summary[0] if summary else None, tuple(n[0] for n in notes))


def notes_to_fold(
    conn: sqlite3.Connection, npc_id: str, character_id: int, keep: int
) -> list[tuple[int, str]]:
    """Unfolded notes beyond the newest ``keep``, oldest first."""
    rows = conn.execute(
        "SELECT id, note FROM npc_memories WHERE npc_id = ? AND character_id = ? AND folded = 0"
        " ORDER BY id",
        (npc_id, character_id),
    ).fetchall()
    return [(r[0], r[1]) for r in rows[: max(0, len(rows) - keep)]]


def fold_memories(
    conn: sqlite3.Connection,
    npc_id: str,
    character_id: int,
    note_ids: list[int],
    summary: str,
) -> None:
    """Replace some notes with a new summary line (the notes stay, marked folded)."""
    line = text(summary, "memory summary", MAX_SUMMARY).strip()
    with atomic(conn):
        conn.execute(
            "INSERT INTO npc_memory_summaries (npc_id, character_id, summary) VALUES (?, ?, ?)"
            " ON CONFLICT DO UPDATE SET summary = excluded.summary",
            (npc_id, character_id, line),
        )
        conn.executemany(
            "UPDATE npc_memories SET folded = 1 WHERE id = ?", [(i,) for i in note_ids]
        )
