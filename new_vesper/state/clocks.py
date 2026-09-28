"""Threat clocks (D6): defined in content, advanced one segment at a time."""

import sqlite3
from dataclasses import dataclass

from new_vesper.rules.errors import require_range
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import as_state_error, require_row, slug, text
from new_vesper.state.world import get_region


@dataclass(frozen=True)
class Clock:
    id: str
    region_id: str
    name: str
    segments: int
    filled: int

    @property
    def full(self) -> bool:
        return self.filled == self.segments


def get_clock(conn: sqlite3.Connection, clock_id: str) -> Clock:
    row = require_row(
        conn.execute("SELECT * FROM threat_clocks WHERE id = ?", (clock_id,)).fetchone(),
        "threat clock",
        clock_id,
    )
    return Clock(row["id"], row["region_id"], row["name"], row["segments"], row["filled"])


def clocks_in(conn: sqlite3.Connection, region_id: str) -> list[Clock]:
    rows = conn.execute(
        "SELECT id FROM threat_clocks WHERE region_id = ? ORDER BY id", (region_id,)
    )
    return [get_clock(conn, row[0]) for row in rows]


def add_clock(
    conn: sqlite3.Connection, clock_id: str, region_id: str, name: str, segments: int, cause: Cause
) -> Clock:
    cid = slug(clock_id, "clock id")
    region = get_region(conn, region_id)
    with as_state_error():
        require_range(segments, "segments", 1, 12)
    with atomic(conn), as_state_error():
        conn.execute(
            "INSERT INTO threat_clocks (id, region_id, name, segments) VALUES (?, ?, ?, ?)",
            (cid, region.id, text(name, "clock name", 80), segments),
        )
        append_event(conn, "clock_added", cause, {"clock_id": cid}, region_id=region.id)
    return get_clock(conn, cid)


def advance_clock(conn: sqlite3.Connection, clock_id: str, cause: Cause) -> Clock:
    """Fill one segment. A full clock cannot advance further."""
    with atomic(conn):
        clock = get_clock(conn, clock_id)
        if clock.full:
            raise StateError(f"threat clock {clock.id} is already full")
        conn.execute("UPDATE threat_clocks SET filled = filled + 1 WHERE id = ?", (clock.id,))
        after = clock.filled + 1
        append_event(
            conn,
            "clock_advanced",
            cause,
            {
                "clock_id": clock.id,
                "filled": after,
                "segments": clock.segments,
                "full": after == clock.segments,
            },
            region_id=clock.region_id,
        )
    return get_clock(conn, clock.id)
