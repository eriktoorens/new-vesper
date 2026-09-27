"""Players: the people behind characters."""

import sqlite3
from dataclasses import dataclass

from new_vesper.state.db import atomic
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import as_state_error, require_row, row_id, text


@dataclass(frozen=True)
class Player:
    id: int
    handle: str
    created_at: str


def create_player(conn: sqlite3.Connection, handle: str, cause: Cause) -> Player:
    with atomic(conn), as_state_error():
        cursor = conn.execute(
            "INSERT INTO players (handle) VALUES (?)", (text(handle, "handle", 40).strip(),)
        )
        player_id = int(cursor.lastrowid or 0)
        append_event(conn, "player_created", cause, {"player_id": player_id})
    return get_player(conn, player_id)


def get_player(conn: sqlite3.Connection, player_id: int) -> Player:
    pid = row_id(player_id, "player id")
    row = require_row(
        conn.execute("SELECT * FROM players WHERE id = ?", (pid,)).fetchone(), "player", pid
    )
    return Player(row["id"], row["handle"], row["created_at"])


def find_player(conn: sqlite3.Connection, handle: str) -> Player | None:
    """The player with this handle, if any."""
    row = conn.execute(
        "SELECT id FROM players WHERE handle = ?", (text(handle, "handle", 40).strip(),)
    ).fetchone()
    return None if row is None else get_player(conn, row[0])
