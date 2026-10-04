"""What an NPC knows about a character (D121): the first slice of D106's belief field.

A holder (an NPC) holds a fact about a subject (a character), learned by hearing
or seeing it. Facts are append-only; once there are too many, the oldest fold
into one summary line, and the folded rows stay, marked.
"""

import sqlite3
from dataclasses import dataclass

from new_vesper.state.errors import StateError
from new_vesper.state.validate import text

MAX_FACT = 160
MAX_SUMMARY = 600
LEARNED = frozenset({"heard", "saw"})
NPC, CHARACTER = "npc", "character"


@dataclass(frozen=True)
class Known:
    summary: str | None  # older facts, folded
    facts: tuple[str, ...]  # newest last


def _one_line(value: object, name: str, max_length: int) -> str:
    clean = text(value, name, max_length).strip()
    if "\n" in clean or "\r" in clean:
        raise StateError(f"{name} must be one line")
    return clean


def known(conn: sqlite3.Connection, npc_id: str, character_id: int) -> Known:
    pair = (NPC, npc_id, CHARACTER, str(character_id))
    rows = conn.execute(
        "SELECT fact FROM held_facts WHERE holder_kind = ? AND holder_id = ? AND about_kind = ?"
        " AND about_id = ? AND folded = 0 ORDER BY id",
        pair,
    ).fetchall()
    summary = conn.execute(
        "SELECT summary FROM held_fact_summaries WHERE holder_kind = ? AND holder_id = ?"
        " AND about_kind = ? AND about_id = ?",
        pair,
    ).fetchone()
    return Known(None if summary is None else summary[0], tuple(r[0] for r in rows))


def learn(
    conn: sqlite3.Connection,
    npc_id: str,
    character_id: int,
    fact: str,
    learned: str,
    scene_id: int | None,
) -> bool:
    """Record a fact; returns False when the NPC already knew exactly this."""
    clean = _one_line(fact, "fact", MAX_FACT)
    if learned not in LEARNED:
        raise StateError(f"learned must be one of {sorted(LEARNED)}")
    if clean.casefold() in {f.casefold() for f in known(conn, npc_id, character_id).facts}:
        return False
    conn.execute(
        "INSERT INTO held_facts"
        " (holder_kind, holder_id, about_kind, about_id, fact, learned, scene_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (NPC, npc_id, CHARACTER, str(character_id), clean, learned, scene_id),
    )
    return True


def facts_to_fold(
    conn: sqlite3.Connection, npc_id: str, character_id: int, keep: int
) -> list[tuple[int, str]]:
    """Unfolded facts beyond the newest ``keep``, oldest first."""
    rows = conn.execute(
        "SELECT id, fact FROM held_facts WHERE holder_kind = ? AND holder_id = ?"
        " AND about_kind = ? AND about_id = ? AND folded = 0 ORDER BY id",
        (NPC, npc_id, CHARACTER, str(character_id)),
    ).fetchall()
    return [(r[0], r[1]) for r in rows[: max(0, len(rows) - keep)]]


def fold(
    conn: sqlite3.Connection, npc_id: str, character_id: int, fact_ids: list[int], summary: str
) -> None:
    """Replace some facts with a summary line; the facts stay, marked folded."""
    line = text(summary, "facts summary", MAX_SUMMARY).strip()
    conn.execute(
        "INSERT INTO held_fact_summaries (holder_kind, holder_id, about_kind, about_id, summary)"
        " VALUES (?, ?, ?, ?, ?) ON CONFLICT DO UPDATE SET summary = excluded.summary",
        (NPC, npc_id, CHARACTER, str(character_id), line),
    )
    conn.executemany("UPDATE held_facts SET folded = 1 WHERE id = ?", [(i,) for i in fact_ids])
