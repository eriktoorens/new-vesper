import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from new_vesper.budget.policy import stamp
from new_vesper.city.weather import current_weather, previous_block
from new_vesper.content.loader import Content, load_content
from new_vesper.content.seed import seed
from new_vesper.rules import clock
from new_vesper.rules.weather import next_weather
from new_vesper.state.db import open_database
from tests.dm.conftest import SeqRng


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def conn(content: Content) -> Iterator[sqlite3.Connection]:
    db = open_database()
    seed(db, content)
    yield db
    db.close()


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_city_clock_is_us_eastern() -> None:
    moment = utc(2026, 9, 28, 1, 40)  # 9:40 pm the evening before, EDT
    assert clock.describe(moment) == "Sunday 9:40 pm, evening"
    assert clock.city_day(moment) == "2026-09-27"
    assert clock.weekday(moment) == "sunday"


@pytest.mark.parametrize(
    ("hour", "part"),
    [
        (0, "small hours"),
        (4, "small hours"),
        (5, "dawn"),
        (7, "morning"),
        (11, "midday"),
        (14, "afternoon"),
        (17, "dusk"),
        (20, "evening"),
        (23, "night"),
    ],
)
def test_parts_of_day(hour: int, part: str) -> None:
    local = datetime(2026, 9, 29, hour, 30, tzinfo=clock.CITY_TZ)
    assert clock.part_of_day(local) == part


def test_day_starts_at_city_midnight_across_daylight_saving() -> None:
    assert clock.day_start_utc(utc(2026, 9, 29, 12)) == utc(2026, 9, 29, 4)  # EDT
    assert clock.day_start_utc(utc(2026, 12, 1, 12)) == utc(2026, 12, 1, 5)  # EST


def test_weather_blocks_across_the_autumn_clock_change() -> None:
    # Clocks fall back at 2:00 am EDT on 1 November 2026: the 00-03 block is 4 hours long.
    late = utc(2026, 11, 1, 7, 30)  # 2:30 am EST
    start = clock.weather_block_start(late)
    assert clock.city_time(start).hour == 0
    assert previous_block(start) == clock.weather_block_start(start - timedelta(hours=2))
    assert clock.city_time(previous_block(start)).hour == 21


def test_naive_times_rejected() -> None:
    with pytest.raises(ValueError):
        clock.city_day(datetime(2026, 1, 1))


def test_next_weather_follows_weights() -> None:
    table = {"rain": {"rain": 3, "fog": 1}, "fog": {"fog": 1}}
    assert next_weather("rain", table, SeqRng(3)) == "rain"
    assert next_weather("rain", table, SeqRng(4)) == "fog"


def test_weather_is_stored_and_shared(conn: sqlite3.Connection, content: Content) -> None:
    now = utc(2026, 9, 29, 16)
    first = current_weather(conn, content, "market", now)
    assert current_weather(conn, content, "market", now + timedelta(minutes=50)) == first
    stored = conn.execute(
        "SELECT weather_id FROM weather WHERE block_start = ?",
        (stamp(clock.weather_block_start(now)),),
    ).fetchone()[0]
    assert stored == first.id


def test_weather_drifts_rather_than_jumps(conn: sqlite3.Connection, content: Content) -> None:
    table = content.regions["market"].weather
    moment = utc(2026, 9, 1, 12)
    seen = []
    for _ in range(300):
        seen.append(current_weather(conn, content, "market", moment).id)
        moment += timedelta(hours=3)
    for before, after in pairwise(seen):
        assert after in table.transitions[before], (before, after)
    order = list(table.states)
    assert all(abs(order.index(a) - order.index(b)) <= 2 for a, b in pairwise(seen))
    assert seen.count("steady-rain") > seen.count("storm")
    assert len(set(seen)) >= 4  # it does change


def test_weather_is_reproducible(content: Content) -> None:
    def sky() -> list[str]:
        db = open_database()
        seed(db, content)
        moment = utc(2026, 9, 1, 12)
        out = []
        for _ in range(20):
            out.append(current_weather(db, content, "market", moment).id)
            moment += timedelta(hours=3)
        return out

    assert sky() == sky()


def test_long_gaps_catch_up_briefly(conn: sqlite3.Connection, content: Content) -> None:
    current_weather(conn, content, "market", utc(2026, 1, 1, 12))
    current_weather(conn, content, "market", utc(2026, 9, 1, 12))
    rows = conn.execute("SELECT COUNT(*) FROM weather").fetchone()[0]
    assert rows <= 2 * 16  # two catch-ups of at most 16 blocks, not months of blocks
