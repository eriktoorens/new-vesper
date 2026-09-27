import sqlite3

import pytest

from new_vesper.rules.resolver import Difficulty, resolve
from new_vesper.rules.stats import Stat
from new_vesper.state import characters, clocks, rolls, scenes
from new_vesper.state.characters import Character
from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM, list_events
from tests.rules.conftest import FixedDice


def _roll(conn: sqlite3.Connection, char: Character, scene_id: int, knack: str | None = None):
    result = resolve(1, Difficulty.RISKY, FixedDice([3, 4]))
    return rolls.record_roll(
        conn,
        char.id,
        scene_id,
        Stat.SLICK,
        Difficulty.RISKY,
        result,
        "slip past the guard",
        SYSTEM,
        knack_id=knack,
    )


def test_roll_round_trip_and_single_use(conn: sqlite3.Connection, mira: Character) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    roll = _roll(conn, mira, scene.id)
    assert (roll.dice, roll.total, roll.tier.value) == ((3, 4), 8, "cost")
    rolls.use_roll(conn, roll.id, rolls.RollUse.CONSEQUENCE)
    with pytest.raises(StateError, match="already been used"):
        rolls.use_roll(conn, roll.id, rolls.RollUse.CONSEQUENCE)
    assert rolls.use_roll(conn, roll.id, rolls.RollUse.LOOT).loot_used
    assert list_events(conn, character_id=mira.id)[-1].kind == "roll"


def test_rolls_cannot_be_rewritten(conn: sqlite3.Connection, mira: Character) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    roll = _roll(conn, mira, scene.id)
    for sql in (
        "UPDATE rolls SET tier = 'clean', total = 12, die_1 = 6, die_2 = 5 WHERE id = ?",
        "UPDATE rolls SET consequence_used = 0 WHERE id = ?",
        "DELETE FROM rolls WHERE id = ?",
    ):
        if "consequence_used = 0" in sql:
            conn.execute("UPDATE rolls SET consequence_used = 1 WHERE id = ?", (roll.id,))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (roll.id,))


def test_forged_total_rejected(conn: sqlite3.Connection, mira: Character) -> None:
    scene = scenes.open_scene(conn, "market", SYSTEM)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO rolls (character_id, scene_id, stat, difficulty, magic, stakes, die_1,"
            " die_2, stat_value, modifier, bonus, total, tier)"
            " VALUES (?, ?, 'steel', 'risky', 0, 's', 1, 1, 0, 0, 0, 12, 'clean')",
            (mira.id, scene.id),
        )


def test_knack_uses(conn: sqlite3.Connection, mira: Character) -> None:
    first = scenes.open_scene(conn, "market", SYSTEM)
    _roll(conn, mira, first.id, "read-the-crowd")
    _roll(conn, mira, first.id, "read-the-crowd")
    _roll(conn, mira, first.id)
    assert rolls.knack_uses(conn, mira.id, "read-the-crowd", scene_id=first.id) == 2
    assert rolls.knack_uses(conn, mira.id, "read-the-crowd", since="2999-01-01") == 0


def test_clock_fills_and_stops(conn: sqlite3.Connection) -> None:
    clock = clocks.add_clock(conn, "the-audit", "market", "The Registry audit", 4, SYSTEM)
    for expected in (1, 2, 3, 4):
        clock = clocks.advance_clock(conn, clock.id, SYSTEM)
        assert clock.filled == expected
    assert clock.full
    with pytest.raises(StateError, match="already full"):
        clocks.advance_clock(conn, clock.id, SYSTEM)
    assert [c.id for c in clocks.clocks_in(conn, "market")] == ["the-audit"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE threat_clocks SET filled = 9 WHERE id = 'the-audit'")


def test_gained_tags_join_origin_tags(conn: sqlite3.Connection, mira: Character) -> None:
    mira = characters.add_character_tag(conn, mira.id, "half-faded", SYSTEM)
    assert mira.tags == {"streetwise", "half-faded"}
    assert characters.add_character_tag(conn, mira.id, "half-faded", SYSTEM) == mira
    with pytest.raises(StateError):
        characters.add_character_tag(conn, mira.id, "Admin; all powers", SYSTEM)
