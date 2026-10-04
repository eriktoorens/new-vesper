"""Bodily needs in storage (D83-D89): each character's level and time toward the next step."""

import sqlite3
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime

from new_vesper.rules.needs import Need, NeedState
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import row_id


def stamp(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_needs(
    conn: sqlite3.Connection, character_id: int, needs: Iterable[Need]
) -> dict[Need, tuple[NeedState, datetime | None]]:
    """Each need's state and the last moment counted (None if never counted)."""
    cid = row_id(character_id, "character id")
    rows = {
        r["need"]: r
        for r in conn.execute("SELECT * FROM character_needs WHERE character_id = ?", (cid,))
    }
    found = {}
    for need in needs:
        row = rows.get(need.value)
        if row is None:
            found[need] = (NeedState(), None)
        else:
            state = NeedState(row["level"], row["accrued"], bool(row["easing"]))
            found[need] = (state, _parse_time(row["updated_at"]))
    return found


def save_needs(
    conn: sqlite3.Connection, character_id: int, states: Mapping[Need, NeedState], now: datetime
) -> None:
    cid = row_id(character_id, "character id")
    conn.executemany(
        "INSERT INTO character_needs (character_id, need, level, accrued, easing, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (character_id, need) DO UPDATE SET"
        " level = excluded.level, accrued = excluded.accrued, easing = excluded.easing,"
        " updated_at = excluded.updated_at",
        [
            (cid, need.value, s.level, s.accrued, int(s.easing), stamp(now))
            for need, s in states.items()
        ],
    )


def resume(
    conn: sqlite3.Connection, character_id: int, needs: Iterable[Need], now: datetime
) -> None:
    """Coming online: time spent offline is never counted (D88)."""
    current = get_needs(conn, character_id, needs)
    save_needs(conn, character_id, {n: s for n, (s, _) in current.items()}, now)


def relieve(
    conn: sqlite3.Connection,
    character_id: int,
    needs: Iterable[Need],
    now: datetime,
    cause: Cause,
    how: str,
) -> None:
    """Clear needs back to nothing, and log how."""
    cleared = list(needs)
    save_needs(conn, character_id, dict.fromkeys(cleared, NeedState()), now)
    append_event(
        conn,
        "needs_relieved",
        cause,
        {"needs": [n.value for n in cleared], "how": how},
        character_id=character_id,
    )
