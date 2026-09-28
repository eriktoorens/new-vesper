import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from new_vesper.city.npcs import present_at, regulars_elsewhere, whereabouts
from new_vesper.city.tick import run_due_ticks
from new_vesper.content.loader import Content, load_content
from new_vesper.content.seed import seed
from new_vesper.rules import clock
from new_vesper.rules.light import apply_deed
from new_vesper.state import world
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM, Actor, Cause, list_events


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def conn(content: Content) -> Iterator[sqlite3.Connection]:
    db = open_database()
    seed(db, content)
    yield db
    db.close()


def city(y: int, mo: int, d: int, h: int, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=clock.CITY_TZ)


def test_default_day(content: Content) -> None:
    nana = content.npcs["nana-priya"]
    tuesday = city(2026, 9, 29, 10, 30)
    assert whereabouts(nana, tuesday).location == "tarp-row"
    assert whereabouts(nana, city(2026, 9, 29, 23)).activity.startswith("asleep")
    assert whereabouts(nana, city(2026, 9, 29, 3)).activity.startswith("asleep")  # wraps


def test_weekly_variation(content: Content) -> None:
    nana, tomas = content.npcs["nana-priya"], content.npcs["tomas-haddad"]
    sunday = city(2026, 9, 27, 13)
    assert whereabouts(nana, sunday).location == "lantern-arcade"
    monday = city(2026, 9, 28, 11)
    assert whereabouts(tomas, monday).location == "weighhouse"
    assert whereabouts(tomas, city(2026, 9, 28, 15)).location is None  # day off, away


def test_whisker_is_gone_below_on_thursday_nights(content: Content) -> None:
    whisker = content.npcs["ferryman-whisker"]
    assert whereabouts(whisker, city(2026, 10, 1, 20)).location is None
    assert whereabouts(whisker, city(2026, 10, 2, 20)).location == "drowned-station"


def test_present_and_regulars_elsewhere(content: Content) -> None:
    noon = city(2026, 9, 29, 12, 15)
    assert {w.npc.id for w in present_at(content, "tarp-row", noon)} == {
        "tomas-haddad",
        "clerk-vasil",
    }
    away = regulars_elsewhere(content, "weighhouse", noon)
    assert [(w.npc.id, w.location) for w in away] == [("clerk-vasil", "tarp-row")]


def test_every_npc_is_always_somewhere(content: Content) -> None:
    moment = city(2026, 9, 28, 0)
    for _ in range(7 * 24 * 4):
        for npc in content.npcs.values():
            where = whereabouts(npc, moment)
            assert where.location is None or where.location in content.locations
        moment += timedelta(minutes=15)


def ticks(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT city_day FROM city_ticks ORDER BY city_day")]


def test_first_tick_is_today_and_idempotent(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    run_due_ticks(conn, content, now)
    assert ticks(conn) == [clock.city_day(now)]


def test_missed_days_are_caught_up(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    run_due_ticks(conn, content, now + timedelta(days=3))
    assert len(ticks(conn)) == 4


def test_long_absences_cap_the_catch_up(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    run_due_ticks(conn, content, now + timedelta(days=60))
    assert len(ticks(conn)) == 1 + 14


def test_neglect_dims_a_region_each_week(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    run_due_ticks(conn, content, now + timedelta(days=6))
    assert world.get_region(conn, "market").light == 6
    run_due_ticks(conn, content, now + timedelta(days=7))
    assert world.get_region(conn, "market").light == 5
    run_due_ticks(conn, content, now + timedelta(days=14))  # caught up: another week
    assert world.get_region(conn, "market").light == 4


def test_raising_light_resets_the_week(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    world.apply_light_change(
        conn,
        "market",
        apply_deed(6, "raise", "deed"),
        Cause(Actor.DM),
        "relit the shrine",
        source="adjust_light",
    )
    run_due_ticks(conn, content, now + timedelta(days=7))
    assert world.get_region(conn, "market").light == 6  # 7 raised, then one neglect


def test_npc_goals_advance(conn: sqlite3.Connection, content: Content) -> None:
    now = datetime.now(UTC)
    run_due_ticks(conn, content, now)
    run_due_ticks(conn, content, now + timedelta(days=2))  # Nana: every 3 days
    events = list_events(conn, kind="npc_goal_advanced", limit=100)
    nana = [e for e in events if e.payload["npc_id"] == "nana-priya"]
    assert len(nana) == 1
    assert nana[0].payload["now"] == content.npcs["nana-priya"].goal.stages[0]
    run_due_ticks(conn, content, now + timedelta(days=13))
    stage = conn.execute("SELECT stage FROM npc_goals WHERE npc_id = 'nana-priya'").fetchone()[0]
    assert stage == len(content.npcs["nana-priya"].goal.stages)  # stops at the last stage


def test_tick_events_are_system_events(conn: sqlite3.Connection, content: Content) -> None:
    run_due_ticks(conn, content, datetime.now(UTC))
    run_due_ticks(conn, content, datetime.now(UTC) + timedelta(days=30))
    assert {e.actor for e in list_events(conn, kind="npc_goal_advanced", limit=100)} == {
        SYSTEM.actor
    }
