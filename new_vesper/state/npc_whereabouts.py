"""Where each NPC is (D111): stored, one place at a time."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from new_vesper.state.errors import StateError


@dataclass(frozen=True)
class Stored:
    npc_id: str
    location_id: str | None  # None: away from the district
    activity: str
    since: datetime
    detour_until: datetime | None = None  # off their agenda until then (D133)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def all_whereabouts(conn: sqlite3.Connection) -> dict[str, Stored]:
    rows = conn.execute(
        "SELECT npc_id, location_id, activity, since, detour_until FROM npc_whereabouts"
    )
    return {
        r["npc_id"]: Stored(
            r["npc_id"],
            r["location_id"],
            r["activity"],
            _parse(r["since"]),
            None if r["detour_until"] is None else _parse(r["detour_until"]),
        )
        for r in rows
    }


def put(
    conn: sqlite3.Connection,
    npc_id: str,
    location_id: str | None,
    activity: str,
    since: datetime,
    detour_until: datetime | None = None,
) -> Stored:
    """Place an NPC: they are here, doing this, from this moment (until, if on a detour)."""
    if not isinstance(npc_id, str) or not npc_id:
        raise StateError("npc id must be a non-empty string")
    if not isinstance(activity, str) or not 1 <= len(activity) <= 200:
        raise StateError("activity must be 1-200 characters")
    conn.execute(
        "INSERT INTO npc_whereabouts (npc_id, location_id, activity, since, detour_until)"
        " VALUES (?, ?, ?, ?, ?) ON CONFLICT (npc_id) DO UPDATE SET"
        " location_id = excluded.location_id, activity = excluded.activity,"
        " since = excluded.since, detour_until = excluded.detour_until",
        (
            npc_id,
            location_id,
            activity,
            _stamp(since),
            None if detour_until is None else _stamp(detour_until),
        ),
    )
    return Stored(npc_id, location_id, activity, since, detour_until)


def watched_locations(conn: sqlite3.Connection, excluding: int | None = None) -> frozenset[str]:
    """Places where a player character is right now: someone is with whoever is there."""
    rows = conn.execute(
        "SELECT DISTINCT location_id FROM characters"
        " WHERE online = 1 AND location_id IS NOT NULL AND id IS NOT ?",
        (excluding,),
    )
    return frozenset(r["location_id"] for r in rows)
