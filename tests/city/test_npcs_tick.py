import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from new_vesper.city.npcs import agenda, everyone, move_on, present_at, regulars_elsewhere
from new_vesper.city.tick import run_due_ticks
from new_vesper.content.loader import Content, load_content
from new_vesper.content.seed import seed
from new_vesper.rules import clock
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.light import apply_deed
from new_vesper.rules.stats import Stat
from new_vesper.state import characters, players, world
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


STATS = {Stat.STEEL: 1, Stat.SLICK: 2, Stat.WIRE: 0, Stat.WEIRD: -1, Stat.HEART: 1}


def city(y: int, mo: int, d: int, h: int, mi: int = 0) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=clock.CITY_TZ)


def test_default_day(content: Content) -> None:
    nana = content.npcs["nana-priya"]
    tuesday = city(2026, 9, 29, 10, 30)
    assert agenda(nana, tuesday).location == "tarp-row"
    assert agenda(nana, city(2026, 9, 29, 23)).activity.startswith("asleep")
    assert agenda(nana, city(2026, 9, 29, 3)).activity.startswith("asleep")  # wraps


def test_weekly_variation(content: Content) -> None:
    nana, tomas = content.npcs["nana-priya"], content.npcs["tomas-haddad"]
    sunday = city(2026, 9, 27, 13)
    assert agenda(nana, sunday).location == "lantern-arcade"
    monday = city(2026, 9, 28, 11)
    assert agenda(tomas, monday).location == "weighhouse"
    assert agenda(tomas, city(2026, 9, 28, 15)).location is None  # day off, away


def test_whisker_is_gone_below_on_thursday_nights(content: Content) -> None:
    whisker = content.npcs["ferryman-whisker"]
    assert agenda(whisker, city(2026, 10, 1, 20)).location is None
    assert agenda(whisker, city(2026, 10, 2, 20)).location == "drowned-station"


def test_present_and_regulars_elsewhere(conn: sqlite3.Connection, content: Content) -> None:
    noon = city(2026, 9, 29, 12, 15)
    assert {w.npc.id for w in present_at(conn, content, "tarp-row", noon)} == {
        "tomas-haddad",
        "clerk-vasil",
    }
    away = regulars_elsewhere(conn, content, "weighhouse", noon)
    assert [(w.npc.id, w.location) for w in away] == [("clerk-vasil", "tarp-row")]


def test_every_npc_is_always_somewhere(content: Content) -> None:
    moment = city(2026, 9, 28, 0)
    for _ in range(7 * 24 * 4):
        for npc in content.npcs.values():
            where = agenda(npc, moment)
            assert where.location is None or where.location in content.locations
        moment += timedelta(minutes=15)


# --- one place at a time (D111-D113) -------------------------------------------


def someone_at(conn: sqlite3.Connection, location: str) -> int:
    """An online player character at this place: someone is with whoever is there."""
    player = players.create_player(conn, f"p{location}", SYSTEM)
    char = characters.create_character(
        conn,
        player.id,
        "Mira",
        "street-born",
        "Nana Priya",
        new_sheet(STATS, ("rooftop-runner", "back-alley-patch")),
        SYSTEM,
        location_id=location,
    )
    characters.set_online(conn, char.id, True, SYSTEM)
    return char.id


def where(conn: sqlite3.Connection, content: Content, npc_id: str, now: datetime) -> str | None:
    return next(w.location for w in everyone(conn, content, now) if w.npc.id == npc_id)


def test_nobody_watching_npcs_follow_their_agenda(
    conn: sqlite3.Connection, content: Content
) -> None:
    before_five = city(2026, 9, 29, 16, 55)
    assert where(conn, content, "nana-priya", before_five) == "hundred-hooks"
    assert where(conn, content, "nana-priya", city(2026, 9, 29, 17, 5)) == "umbrella-shrine"
    moved = list_events(conn, kind="npc_moved")
    assert [e.payload for e in moved if e.payload["npc_id"] == "nana-priya"] == [
        {"npc_id": "nana-priya", "from": "hundred-hooks", "to": "umbrella-shrine"}
    ]


def test_an_npc_someone_is_with_stays_put(conn: sqlite3.Connection, content: Content) -> None:
    # Fourth playtest: Nana Priya vanished mid-conversation at 5:00.
    where(conn, content, "nana-priya", city(2026, 9, 29, 16, 55))
    someone_at(conn, "hundred-hooks")
    late = city(2026, 9, 29, 17, 30)
    nana = next(w for w in present_at(conn, content, "hundred-hooks", late))
    assert nana.npc.id == "nana-priya" and not nana.on_agenda
    assert nana.agenda.location == "umbrella-shrine" and nana.agenda.starts == 17 * 60
    assert where(conn, content, "nana-priya", late) == "hundred-hooks"  # never in two places


def test_once_nobody_is_with_them_a_late_npc_goes_on_to_their_next_errand(
    conn: sqlite3.Connection, content: Content
) -> None:
    where(conn, content, "nana-priya", city(2026, 9, 29, 16, 55))
    char_id = someone_at(conn, "hundred-hooks")
    assert where(conn, content, "nana-priya", city(2026, 9, 29, 17, 30)) == "hundred-hooks"
    characters.set_online(conn, char_id, False, SYSTEM)
    assert where(conn, content, "nana-priya", city(2026, 9, 29, 17, 31)) == "umbrella-shrine"


def test_npcs_still_arrive_where_someone_is(conn: sqlite3.Connection, content: Content) -> None:
    where(conn, content, "nana-priya", city(2026, 9, 29, 16, 55))
    someone_at(conn, "umbrella-shrine")
    assert where(conn, content, "nana-priya", city(2026, 9, 29, 17, 5)) == "umbrella-shrine"


def test_moving_on_follows_the_agenda(conn: sqlite3.Connection, content: Content) -> None:
    where(conn, content, "nana-priya", city(2026, 9, 29, 16, 55))
    someone_at(conn, "hundred-hooks")
    late = city(2026, 9, 29, 17, 20)
    cause = Cause(Actor.DM, None, None)
    before, after = move_on(conn, content, "nana-priya", late, cause, "her offering can't wait")
    assert (before.location, after.location) == ("hundred-hooks", "umbrella-shrine")
    assert after.on_agenda
    assert present_at(conn, content, "hundred-hooks", late) == []
    [event] = list_events(conn, kind="npc_moved_on")
    assert event.payload["reason"] == "her offering can't wait"
    assert event.actor == Actor.DM.value


def test_an_npc_is_in_one_place_at_every_moment(conn: sqlite3.Connection, content: Content) -> None:
    someone_at(conn, "tarp-row")
    moment = city(2026, 9, 28, 0)
    for _ in range(2 * 24 * 4):
        seen = [w.npc.id for w in everyone(conn, content, moment)]
        assert sorted(seen) == sorted(content.npcs)
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
