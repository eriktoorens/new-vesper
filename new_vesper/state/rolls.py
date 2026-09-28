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
    # A gist roll's language (D78), and the consequence a roll paid, once it has.
    language_id: str | None = None
    consequence_type: str | None = None


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
        language_id=row["language_id"],
        consequence_type=row["consequence_type"],
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
    language_id: str | None = None,
) -> Roll:
    what = text(stakes, "stakes", 300)
    with atomic(conn):
        cursor = conn.execute(
            "INSERT INTO rolls (character_id, scene_id, stat, difficulty, knack_id, magic, stakes,"
            " die_1, die_2, stat_value, modifier, bonus, total, tier, language_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                language_id,
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
                "language": language_id,
            },
            character_id=character_id,
        )
    return get_roll(conn, roll_id)


def use_roll(
    conn: sqlite3.Connection, roll_id: int, use: RollUse, consequence_type: str | None = None
) -> Roll:
    """Mark a roll as used for a consequence or a loot grant. Each use happens once.

    A consequence records its type, since a gist roll's cost decides what is heard.
    """
    column = f"{RollUse(use).value}_used"
    with atomic(conn):
        roll = get_roll(conn, roll_id)
        if getattr(roll, column):
            raise StateError(f"roll {roll.id} has already been used for {use}")
        conn.execute(f"UPDATE rolls SET {column} = 1 WHERE id = ?", (roll.id,))
        if use is RollUse.CONSEQUENCE and consequence_type is not None:
            conn.execute(
                "UPDATE rolls SET consequence_type = ? WHERE id = ?",
                (text(consequence_type, "consequence type", 40), roll.id),
            )
    return get_roll(conn, roll.id)


def gist_rolls(conn: sqlite3.Connection, character_id: int, scene_id: int) -> list[Roll]:
    """This character's rolls to follow a language in this scene (D78)."""
    rows = conn.execute(
        "SELECT * FROM rolls WHERE character_id = ? AND scene_id = ? AND language_id IS NOT NULL"
        " ORDER BY id",
        (row_id(character_id, "character id"), row_id(scene_id, "scene id")),
    )
    return [_roll(row) for row in rows]


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
