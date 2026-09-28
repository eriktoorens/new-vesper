"""The favor ledger: every favor owed to a god. Append-only; gods collect."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.state.characters import get_character
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import require_row, row_id, slug, text


class FavorStatus(StrEnum):
    OWED = "owed"
    COLLECTED = "collected"


@dataclass(frozen=True)
class Favor:
    id: int
    character_id: int
    god_id: str
    reason: str
    status: FavorStatus
    created_at: str
    collected_at: str | None


def get_favor(conn: sqlite3.Connection, favor_id: int) -> Favor:
    fid = row_id(favor_id, "favor id")
    row = require_row(
        conn.execute("SELECT * FROM favors WHERE id = ?", (fid,)).fetchone(), "favor", fid
    )
    return Favor(
        row["id"],
        row["character_id"],
        row["god_id"],
        row["reason"],
        FavorStatus(row["status"]),
        row["created_at"],
        row["collected_at"],
    )


def record_favor(
    conn: sqlite3.Connection, character_id: int, god_id: str, reason: str, cause: Cause
) -> Favor:
    character = get_character(conn, character_id)
    god = slug(god_id, "god id")
    why = text(reason, "reason", 300)
    with atomic(conn):
        cursor = conn.execute(
            "INSERT INTO favors (character_id, god_id, reason) VALUES (?, ?, ?)",
            (character.id, god, why),
        )
        favor_id = int(cursor.lastrowid or 0)
        append_event(
            conn,
            "favor_owed",
            cause,
            {"favor_id": favor_id, "god_id": god, "reason": why},
            character_id=character.id,
        )
    return get_favor(conn, favor_id)


def collect_favor(conn: sqlite3.Connection, favor_id: int, cause: Cause) -> Favor:
    with atomic(conn):
        favor = get_favor(conn, favor_id)
        if favor.status is not FavorStatus.OWED:
            raise StateError(f"favor {favor.id} was already collected")
        conn.execute(
            "UPDATE favors SET status = 'collected',"
            " collected_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
            (favor.id,),
        )
        append_event(
            conn,
            "favor_collected",
            cause,
            {"favor_id": favor.id, "god_id": favor.god_id},
            character_id=favor.character_id,
        )
    return get_favor(conn, favor.id)


def favors_owed(conn: sqlite3.Connection, character_id: int) -> list[Favor]:
    cid = get_character(conn, character_id).id
    rows = conn.execute(
        "SELECT id FROM favors WHERE character_id = ? AND status = 'owed' ORDER BY id", (cid,)
    )
    return [get_favor(conn, row[0]) for row in rows]
