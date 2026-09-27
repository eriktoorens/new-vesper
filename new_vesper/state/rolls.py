"""Rolls: every roll code makes, and whether it has been used up (D1)."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from new_vesper.rules.resolver import Difficulty, RollResult, Tier
from new_vesper.rules.stats import Stat
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import require_row, row_id, text


class RollUse(StrEnum):
    CONSEQUENCE = "consequence"
    LOOT = "loot"


@dataclass(frozen=True)
class Roll:
    id: int
    character_id: int
    scene_id: int
    stat: Stat
    difficulty: Difficulty
    knack_id: str | None
    magic: bool
    stakes: str
    dice: tuple[int, int]
    total: int
    tier: Tier
    consequence_used: bool
    loot_used: bool
    created_at: str


def _roll(row: sqlite3.Row) -> Roll:
    return Roll(
        id=row["id"],
        character_id=row["character_id"],
        scene_id=row["scene_id"],
        stat=Stat(row["stat"]),
        difficulty=Difficulty(row["difficulty"]),
        knack_id=row["knack_id"],
        magic=bool(row["magic"]),
        stakes=row["stakes"],
        dice=(row["die_1"], row["die_2"]),
        total=row["total"],
        tier=Tier(row["tier"]),
        consequence_used=bool(row["consequence_used"]),
        loot_used=bool(row["loot_used"]),
        created_at=row["created_at"],
    )


def get_roll(conn: sqlite3.Connection, roll_id: int) -> Roll:
    rid = row_id(roll_id, "roll id")
    return _roll(
        require_row(
            conn.execute("SELECT * FROM rolls WHERE id = ?", (rid,)).fetchone(), "roll", rid
        )
    )


def record_roll(
    conn: sqlite3.Connection,
    character_id: int,
    scene_id: int,
    stat: Stat,
    difficulty: Difficulty,
    result: RollResult,
    stakes: str,
    cause: Cause,
    *,
    knack_id: str | None = None,
    magic: bool = False,
) -> Roll:
    what = text(stakes, "stakes", 300)
    with atomic(conn):
        cursor = conn.execute(
            "INSERT INTO rolls (character_id, scene_id, stat, difficulty, knack_id, magic, stakes,"
            " die_1, die_2, stat_value, modifier, bonus, total, tier)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row_id(character_id, "character id"),
                row_id(scene_id, "scene id"),
                stat.value,
                difficulty.value,
                knack_id,
                int(magic),
                what,
                *result.dice,
                result.stat_value,
                result.modifier,
                result.bonus,
                result.total,
                result.tier.value,
            ),
        )
        roll_id = int(cursor.lastrowid or 0)
        append_event(
            conn,
            "roll",
            cause,
            {
                "roll_id": roll_id,
                "stat": stat.value,
                "difficulty": difficulty.value,
                "knack_id": knack_id,
                "magic": magic,
                "dice": list(result.dice),
                "total": result.total,
                "tier": result.tier.value,
                "stakes": what,
            },
            character_id=character_id,
        )
    return get_roll(conn, roll_id)


def use_roll(conn: sqlite3.Connection, roll_id: int, use: RollUse) -> Roll:
    """Mark a roll as used for a consequence or a loot grant. Each use happens once."""
    column = f"{RollUse(use).value}_used"
    with atomic(conn):
        roll = get_roll(conn, roll_id)
        if getattr(roll, column):
            raise StateError(f"roll {roll.id} has already been used for {use}")
        conn.execute(f"UPDATE rolls SET {column} = 1 WHERE id = ?", (roll.id,))
    return get_roll(conn, roll.id)


def knack_uses(
    conn: sqlite3.Connection,
    character_id: int,
    knack_id: str,
    *,
    scene_id: int | None = None,
    since: str | None = None,
) -> int:
    """How many rolls this character has made with a knack, in a scene or since a time."""
    sql = "SELECT COUNT(*) FROM rolls WHERE character_id = ? AND knack_id = ?"
    params: list[object] = [character_id, knack_id]
    if scene_id is not None:
        sql += " AND scene_id = ?"
        params.append(scene_id)
    if since is not None:
        sql += " AND created_at >= ?"
        params.append(since)
    return int(conn.execute(sql, params).fetchone()[0])
