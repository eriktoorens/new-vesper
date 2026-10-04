"""NPC moods (D119)."""

import sqlite3
from dataclasses import dataclass

from new_vesper.state.errors import StateError
from new_vesper.state.validate import text


@dataclass(frozen=True)
class Mood:
    mood: str
    source: str  # "rolled" or "narrator"
    reason: str | None


def _one_line(value: object, name: str, max_length: int) -> str:
    clean = text(value, name, max_length).strip()
    if "\n" in clean or "\r" in clean:
        raise StateError(f"{name} must be one line")
    return clean


def mood_today(conn: sqlite3.Connection, npc_id: str, city_day: str) -> Mood | None:
    row = conn.execute(
        "SELECT mood, source, reason FROM npc_moods WHERE npc_id = ? AND city_day = ?"
        " ORDER BY id DESC LIMIT 1",
        (npc_id, city_day),
    ).fetchone()
    return None if row is None else Mood(row["mood"], row["source"], row["reason"])


def add_mood(
    conn: sqlite3.Connection,
    npc_id: str,
    city_day: str,
    mood: str,
    source: str,
    *,
    reason: str | None = None,
    scene_id: int | None = None,
) -> Mood:
    clean = _one_line(mood, "mood", 60)
    why = None if reason is None else _one_line(reason, "reason", 300)
    conn.execute(
        "INSERT INTO npc_moods (npc_id, city_day, mood, source, reason, scene_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (npc_id, city_day, clean, source, why, scene_id),
    )
    return Mood(clean, source, why)


def shifted_in_scene(conn: sqlite3.Connection, npc_id: str, scene_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM npc_moods WHERE npc_id = ? AND scene_id = ? AND source = 'narrator'",
        (npc_id, scene_id),
    ).fetchone()
    return row is not None
