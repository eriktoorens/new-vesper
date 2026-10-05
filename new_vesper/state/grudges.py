"""Grudges NPCs hold against each other, and amends between them (D129, D142, D143).

One standing grudge per holder and target: 'held', or 'on_condition' while a condition
from amends is outstanding. It ends 'faded' or 'amended'; the row stays.
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from new_vesper.rules.attitudes import Axis
from new_vesper.rules.grudges import GRUDGE_AXES, AmendsRoll
from new_vesper.state.errors import StateError
from new_vesper.state.validate import text

STANDING = ("held", "on_condition")
ENDINGS = frozenset({"faded", "amended"})


@dataclass(frozen=True)
class Grudge:
    id: int
    holder: str
    target: str
    trust_steps: int
    fondness_steps: int
    betrayal: bool
    reason: str
    status: str
    renewed_at: datetime
    condition_want_id: int | None
    refused_until: datetime | None

    @property
    def depth(self) -> int:
        return self.trust_steps + self.fondness_steps

    def steps(self, axis: Axis) -> int:
        return {Axis.TRUST: self.trust_steps, Axis.FONDNESS: self.fondness_steps}.get(axis, 0)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value.replace("Z", "+00:00"))


def _grudge(row: sqlite3.Row) -> Grudge:
    renewed = _parse(row["renewed_at"])
    assert renewed is not None
    return Grudge(
        row["id"],
        row["holder_npc"],
        row["target_npc"],
        row["trust_steps"],
        row["fondness_steps"],
        bool(row["betrayal"]),
        row["reason"],
        row["status"],
        renewed,
        row["condition_want_id"],
        _parse(row["refused_until"]),
    )


def standing(conn: sqlite3.Connection, holder: str, target: str) -> Grudge | None:
    row = conn.execute(
        "SELECT * FROM npc_grudges WHERE holder_npc = ? AND target_npc = ?"
        " AND status IN ('held', 'on_condition')",
        (holder, target),
    ).fetchone()
    return None if row is None else _grudge(row)


def all_standing(conn: sqlite3.Connection, holder: str | None = None) -> list[Grudge]:
    """Standing grudges, oldest first: one NPC's, or everyone's."""
    query = "SELECT * FROM npc_grudges WHERE status IN ('held', 'on_condition')"
    args: tuple[str, ...] = ()
    if holder is not None:
        query += " AND holder_npc = ?"
        args = (holder,)
    return [_grudge(r) for r in conn.execute(query + " ORDER BY id", args)]


def blocks(conn: sqlite3.Connection, holder: str, target: str, axis: Axis) -> bool:
    """A standing grudge keeps its axes from rising by any route (D143)."""
    found = standing(conn, holder, target)
    return found is not None and found.steps(axis) > 0


def record_drop(
    conn: sqlite3.Connection,
    holder: str,
    target: str,
    axis: Axis,
    betrayal: bool,
    reason: str,
    now: datetime,
    scene_id: int | None,
) -> Grudge:
    """A drop from learning of a tension starts a grudge, or deepens and renews one.

    A grudge waiting on a condition goes back to held: the new wrong undoes the terms.
    """
    if axis not in GRUDGE_AXES:
        raise StateError(f"a grudge is held on trust or fondness, not {axis.value}")
    if holder == target:
        raise StateError("an NPC holds no grudge against themselves")
    why = text(reason, "reason", 300).strip()
    column = f"{axis.value}_steps"
    found = standing(conn, holder, target)
    if found is None:
        conn.execute(
            f"INSERT INTO npc_grudges (holder_npc, target_npc, {column}, betrayal, reason,"
            " renewed_at, scene_id) VALUES (?, ?, 1, ?, ?, ?, ?)",
            (holder, target, int(betrayal), why, _stamp(now), scene_id),
        )
    else:
        conn.execute(
            f"UPDATE npc_grudges SET {column} = {column} + 1, betrayal = max(betrayal, ?),"
            " reason = ?, renewed_at = ?, status = 'held', condition_want_id = NULL"
            " WHERE id = ?",
            (int(betrayal), why, _stamp(now), found.id),
        )
    result = standing(conn, holder, target)
    assert result is not None
    return result


def end(conn: sqlite3.Connection, grudge_id: int, ending: str, scene_id: int | None) -> None:
    if ending not in ENDINGS:
        raise StateError(f"a grudge ends as one of {sorted(ENDINGS)}")
    updated = conn.execute(
        "UPDATE npc_grudges SET status = ?, ended_scene_id = ? WHERE id = ?"
        " AND status IN ('held', 'on_condition')",
        (ending, scene_id, grudge_id),
    ).rowcount
    if not updated:
        raise StateError(f"no standing grudge {grudge_id}")


def on_condition(conn: sqlite3.Connection, grudge_id: int, want_id: int) -> None:
    """Amends accepted on a condition: the grudge waits on that want being met (D142)."""
    conn.execute(
        "UPDATE npc_grudges SET status = 'on_condition', condition_want_id = ? WHERE id = ?",
        (want_id, grudge_id),
    )


def refuse(conn: sqlite3.Connection, grudge_id: int, until: datetime) -> None:
    conn.execute(
        "UPDATE npc_grudges SET refused_until = ? WHERE id = ?", (_stamp(until), grudge_id)
    )


def amends_tried(conn: sqlite3.Connection, grudge_id: int, scene_id: int | None) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM npc_amends WHERE grudge_id = ? AND scene_id IS ?",
            (grudge_id, scene_id),
        ).fetchone()
        is not None
    )


def record_amends(
    conn: sqlite3.Connection,
    grudge_id: int,
    offer: str,
    condition: str,
    roll: AmendsRoll,
    scene_id: int | None,
) -> None:
    conn.execute(
        "INSERT INTO npc_amends (grudge_id, offer, condition, die_one, die_two, fondness,"
        " total, outcome, scene_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            grudge_id,
            offer,
            condition,
            *roll.dice,
            roll.fondness,
            roll.total,
            roll.outcome.value,
            scene_id,
        ),
    )


def conditions_met(conn: sqlite3.Connection) -> list[Grudge]:
    """Grudges whose amends condition, a want, has been recorded as met."""
    rows = conn.execute(
        "SELECT g.* FROM npc_grudges g JOIN npc_wants w ON w.id = g.condition_want_id"
        " WHERE g.status = 'on_condition' AND w.status = 'met' ORDER BY g.id"
    )
    return [_grudge(r) for r in rows]
