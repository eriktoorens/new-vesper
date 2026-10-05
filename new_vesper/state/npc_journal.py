"""What each NPC wants now, wants in tension or alliance, and who knows (D124, D126,
D128, D130, D141).

Wants are one set per NPC, shared by every player. Code changes them only at scene
close, for a reason from the scene; an ended want keeps its row, marked met or dropped.
A tension or alliance lasts while both its wants are current.
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


@dataclass(frozen=True)
class Alliance:
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
    if bond_kind(conn, a, b) == "alliance":
        raise StateError("those wants already pull together")
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


def add_alliance(
    conn: sqlite3.Connection, first: int, second: int, note: str, scene_id: int | None
) -> Alliance:
    """Two NPCs' current wants pull together (D130, D141)."""
    if first == second:
        raise StateError("a want is not allied with itself")
    a, b = sorted((first, second))
    if get_active(conn, a).npc_id == get_active(conn, b).npc_id:
        raise StateError("an alliance is between two NPCs' wants")
    clean = _one_line(note, "alliance", 160)
    kind = bond_kind(conn, a, b)
    if kind == "alliance":
        raise StateError("those wants already pull together")
    if kind == "tension":
        raise StateError("those wants are in tension")
    conn.execute(
        "INSERT INTO npc_want_alliances (want_a, want_b, note, scene_id) VALUES (?, ?, ?, ?)",
        (a, b, clean, scene_id),
    )
    return Alliance(a, b, clean)


def alliances_with(conn: sqlite3.Connection, want_ids: set[int]) -> list[Alliance]:
    """Alliances touching any of these wants, while both wants are still current."""
    rows = conn.execute(
        "SELECT t.want_a, t.want_b, t.note FROM npc_want_alliances t"
        " JOIN npc_wants a ON a.id = t.want_a JOIN npc_wants b ON b.id = t.want_b"
        " WHERE a.status = 'active' AND b.status = 'active' ORDER BY t.id"
    )
    return [Alliance(r[0], r[1], r[2]) for r in rows if r[0] in want_ids or r[1] in want_ids]


def bond_kind(conn: sqlite3.Connection, first: int, second: int) -> str | None:
    """'tension' or 'alliance' if these two wants are current and bound; else None."""
    a, b = sorted((first, second))
    for kind, table in (("tension", "npc_want_tensions"), ("alliance", "npc_want_alliances")):
        found = conn.execute(
            f"SELECT 1 FROM {table} t JOIN npc_wants x ON x.id = t.want_a"
            " JOIN npc_wants y ON y.id = t.want_b"
            " WHERE t.want_a = ? AND t.want_b = ? AND x.status = 'active'"
            " AND y.status = 'active'",
            (a, b),
        ).fetchone()
        if found:
            return kind
    return None


def allied(conn: sqlite3.Connection, npc_a: str, npc_b: str) -> bool:
    """Whether these two NPCs share a current alliance (D143)."""
    rows = conn.execute(
        "SELECT x.npc_id, y.npc_id FROM npc_want_alliances t"
        " JOIN npc_wants x ON x.id = t.want_a JOIN npc_wants y ON y.id = t.want_b"
        " WHERE x.status = 'active' AND y.status = 'active'"
    )
    return any({r[0], r[1]} == {npc_a, npc_b} for r in rows)


def parties(conn: sqlite3.Connection, first: int, second: int, npc_id: str) -> tuple[str, str]:
    """This NPC's part and the other's in a current tension or alliance, as (kind, other).

    Refused unless the two wants are bound, this NPC holds one and someone else the other.
    """
    kind = bond_kind(conn, first, second)
    if kind is None:
        raise StateError(f"wants {first} and {second} are not a current tension or alliance")
    owners = (get_active(conn, first).npc_id, get_active(conn, second).npc_id)
    if npc_id not in owners:
        raise StateError(f"{npc_id} holds neither want")
    other = owners[1] if owners[0] == npc_id else owners[0]
    if other == npc_id:
        raise StateError("both wants are their own; there is no other part to know")
    return kind, other


def mark_knows(
    conn: sqlite3.Connection, npc_id: str, first: int, second: int, how: str, scene_id: int | None
) -> str:
    """This NPC now knows the other party's part (D128). Returns the other NPC's id."""
    kind, other = parties(conn, first, second, npc_id)
    clean = _one_line(how, "how it came out", 160)
    a, b = sorted((first, second))
    if knows(conn, npc_id, a, b):
        raise StateError(f"{npc_id} already knows")
    conn.execute(
        "INSERT INTO npc_bond_knows (kind, want_a, want_b, npc_id, how, scene_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (kind, a, b, npc_id, clean, scene_id),
    )
    return other


def knows(conn: sqlite3.Connection, npc_id: str, first: int, second: int) -> bool:
    """Whether this NPC knows the other's part in the bond on these two wants."""
    a, b = sorted((first, second))
    kind = bond_kind(conn, a, b)
    return kind is not None and (
        conn.execute(
            "SELECT 1 FROM npc_bond_knows WHERE kind = ? AND want_a = ? AND want_b = ?"
            " AND npc_id = ?",
            (kind, a, b, npc_id),
        ).fetchone()
        is not None
    )


def knowers(conn: sqlite3.Connection, first: int, second: int) -> list[str]:
    """Who knows the other's part in this bond, in the order they learned."""
    a, b = sorted((first, second))
    kind = bond_kind(conn, a, b)
    rows = conn.execute(
        "SELECT npc_id FROM npc_bond_knows WHERE kind = ? AND want_a = ? AND want_b = ?"
        " ORDER BY id",
        (kind, a, b),
    )
    return [r[0] for r in rows]
