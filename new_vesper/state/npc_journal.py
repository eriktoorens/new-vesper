"""What each NPC wants now, and wants in tension (D124, D126).

Wants are one set per NPC, shared by every player. Code changes them only at scene
close, for a reason from the scene; an ended want keeps its row, marked met or dropped.
"""

import sqlite3
from dataclasses import dataclass

from new_vesper.state.errors import StateError
from new_vesper.state.validate import text

# Current wants an NPC may hold at once.
MAX_ACTIVE = 4
ENDINGS = frozenset({"met", "dropped"})


@dataclass(frozen=True)
class Want:
    id: int
    npc_id: str
    want: str
    about: str | None
    reason: str


@dataclass(frozen=True)
class Tension:
    want_a: int
    want_b: int
    note: str


def _one_line(value: object, name: str, max_length: int) -> str:
    clean = text(value, name, max_length).strip()
    if "\n" in clean or "\r" in clean:
        raise StateError(f"{name} must be one line")
    return clean


def _want(row: sqlite3.Row) -> Want:
    return Want(row["id"], row["npc_id"], row["want"], row["about"], row["reason"])


def active_wants(conn: sqlite3.Connection, npc_id: str | None = None) -> list[Want]:
    """Current wants, oldest first: one NPC's, or everyone's."""
    if npc_id is None:
        rows = conn.execute("SELECT * FROM npc_wants WHERE status = 'active' ORDER BY id")
    else:
        rows = conn.execute(
            "SELECT * FROM npc_wants WHERE status = 'active' AND npc_id = ? ORDER BY id",
            (npc_id,),
        )
    return [_want(r) for r in rows]


def add_want(
    conn: sqlite3.Connection,
    npc_id: str,
    want: str,
    about: str | None,
    reason: str,
    scene_id: int | None,
) -> Want:
    clean = _one_line(want, "want", 160)
    why = _one_line(reason, "reason", 300)
    who = None if about is None else _one_line(about, "about", 80)
    held = active_wants(conn, npc_id)
    if len(held) >= MAX_ACTIVE:
        raise StateError(f"{npc_id} already holds {MAX_ACTIVE} wants")
    if clean.casefold() in {w.want.casefold() for w in held}:
        raise StateError(f"{npc_id} already wants that")
    cursor = conn.execute(
        "INSERT INTO npc_wants (npc_id, want, about, reason, scene_id) VALUES (?, ?, ?, ?, ?)",
        (npc_id, clean, who, why, scene_id),
    )
    return Want(int(cursor.lastrowid or 0), npc_id, clean, who, why)


def get_active(conn: sqlite3.Connection, want_id: int) -> Want:
    row = conn.execute(
        "SELECT * FROM npc_wants WHERE id = ? AND status = 'active'", (want_id,)
    ).fetchone()
    if row is None:
        raise StateError(f"no current want {want_id}")
    return _want(row)


def end_want(
    conn: sqlite3.Connection, want_id: int, ending: str, reason: str, scene_id: int | None
) -> Want:
    """A want is met or dropped, for a reason; its tensions end with it."""
    if ending not in ENDINGS:
        raise StateError(f"a want ends as one of {sorted(ENDINGS)}")
    found = get_active(conn, want_id)
    why = _one_line(reason, "reason", 300)
    conn.execute(
        "UPDATE npc_wants SET status = ?, ended_reason = ?, ended_scene_id = ? WHERE id = ?",
        (ending, why, scene_id, want_id),
    )
    return found


def add_tension(
    conn: sqlite3.Connection, first: int, second: int, note: str, scene_id: int | None
) -> Tension:
    """Two current wants pull against each other: one NPC's own, or two NPCs'."""
    if first == second:
        raise StateError("a want is not in tension with itself")
    a, b = sorted((first, second))
    get_active(conn, a)
    get_active(conn, b)
    clean = _one_line(note, "tension", 160)
    if conn.execute(
        "SELECT 1 FROM npc_want_tensions WHERE want_a = ? AND want_b = ?", (a, b)
    ).fetchone():
        raise StateError("those wants are already in tension")
    conn.execute(
        "INSERT INTO npc_want_tensions (want_a, want_b, note, scene_id) VALUES (?, ?, ?, ?)",
        (a, b, clean, scene_id),
    )
    return Tension(a, b, clean)


def tensions_with(conn: sqlite3.Connection, want_ids: set[int]) -> list[Tension]:
    """Tensions touching any of these wants, while both wants are still current."""
    rows = conn.execute(
        "SELECT t.want_a, t.want_b, t.note FROM npc_want_tensions t"
        " JOIN npc_wants a ON a.id = t.want_a JOIN npc_wants b ON b.id = t.want_b"
        " WHERE a.status = 'active' AND b.status = 'active' ORDER BY t.id"
    )
    return [Tension(r[0], r[1], r[2]) for r in rows if r[0] in want_ids or r[1] in want_ids]
