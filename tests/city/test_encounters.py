import json
import random
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from new_vesper.city.encounters import (
    NoSuchEncounter,
    ideas_here,
    left_today,
    make_stranger,
    recent_in_district,
    spend,
    todays_pool,
)
from new_vesper.content.loader import Content, load_content, load_documents
from new_vesper.content.model import ContentError
from new_vesper.content.seed import seed
from new_vesper.rules.encounters import Kind
from new_vesper.rules.light import encroach
from new_vesper.rules.sky import TideState, tide
from new_vesper.state import players, world
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM, list_events
from tests.dm.conftest import make_character

DATA = Path(__file__).resolve().parents[2] / "new_vesper" / "content" / "data"
TUESDAY_NOON = datetime(2026, 9, 29, 16, tzinfo=UTC)


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


@pytest.fixture
def conn(content: Content) -> Iterator[sqlite3.Connection]:
    db = open_database()
    seed(db, content)
    players.create_player(db, "ash", SYSTEM)
    yield db
    db.close()


def test_pool_is_rolled_once_per_district_day(conn: sqlite3.Connection) -> None:
    first = todays_pool(conn, "market", TUESDAY_NOON)
    assert 3 <= len(first) <= 6  # the Market is at Light 6
    assert todays_pool(conn, "market", TUESDAY_NOON + timedelta(hours=5)) == first
    other = open_database()
    seed(other, load_content())
    assert todays_pool(other, "market", TUESDAY_NOON) == first  # the same for everyone
    tomorrow = todays_pool(conn, "market", TUESDAY_NOON + timedelta(days=1))
    assert conn.execute("SELECT COUNT(DISTINCT city_day) FROM encounter_pool").fetchone()[0] == 2
    assert tomorrow is not None


def test_spending_uses_a_slot_of_that_kind(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")
    left = left_today(conn, "market", TUESDAY_NOON)
    kind = next(Kind(k) for k, n in left.items() if n and k in {k.value for k in Kind})
    underside, stranger = spend(
        conn,
        content,
        char.id,
        "tarp-row",
        kind,
        "A cook drops a whole pot of broth at Mira's feet.",
        "a cook",
        TUESDAY_NOON,
        SYSTEM,
    )
    assert not underside
    assert stranger is not None and stranger.role == "a cook"
    after = left_today(conn, "market", TUESDAY_NOON)
    assert after[kind.value] == left[kind.value] - 1
    [event] = list_events(conn, kind="encounter")
    assert event.payload["text"].startswith("A cook drops")


def test_an_empty_kind_is_refused(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")
    left = left_today(conn, "market", TUESDAY_NOON)
    for kind in Kind:
        for _ in range(left[kind.value]):
            spend(conn, content, char.id, "tarp-row", kind, "something", None, TUESDAY_NOON, SYSTEM)
    with pytest.raises(NoSuchEncounter, match="no color encounters left"):
        spend(conn, content, char.id, "tarp-row", Kind.COLOR, "more", None, TUESDAY_NOON, SYSTEM)


def test_recent_encounters_are_shown_to_avoid_repeats(
    conn: sqlite3.Connection, content: Content
) -> None:
    char = make_character(conn, location="tarp-row")
    kind = next(
        Kind(k)
        for k, n in left_today(conn, "market", TUESDAY_NOON).items()
        if n and k in {k.value for k in Kind}
    )
    spend(
        conn,
        content,
        char.id,
        "tarp-row",
        kind,
        "A boy lifts Mira's purse.",
        None,
        TUESDAY_NOON,
        SYSTEM,
    )
    recent = recent_in_district(conn, "market", TUESDAY_NOON + timedelta(days=1))
    assert recent == [{"kind": kind.value, "what_happened": "A boy lifts Mira's purse."}]
    assert recent_in_district(conn, "market", TUESDAY_NOON + timedelta(days=4)) == []


def test_ideas_follow_conditions(conn: sqlite3.Connection, content: Content) -> None:
    ideas = {i["idea"][:20] for i in ideas_here(conn, content, "tarp-row", TUESDAY_NOON)}
    assert any(i.startswith("Two cart owners") for i in ideas)
    moment = TUESDAY_NOON
    while tide(moment).state is not TideState.LOW:
        moment += timedelta(minutes=10)
    stairs = ideas_here(conn, content, "tidewater-stairs", moment)
    assert any("Eel-sellers" in i["idea"] for i in stairs)


def test_strangers_speak_the_neighborhood(content: Content) -> None:
    rng = random.Random(4)
    tarp = [make_stranger(content, "tarp-row", False, "a cook", rng).language for _ in range(400)]
    stairs = [
        make_stranger(content, "tidewater-stairs", False, "a sailor", rng).language
        for _ in range(400)
    ]
    assert tarp.count("cantonese") > tarp.count("portuguese") * 2
    assert stairs.count("portuguese") > tarp.count("portuguese")
    assert "animal-speech" not in tarp and "underside-cant" not in tarp
    assert make_stranger(content, "weighhouse", True, "a ghost", rng).language == "underside-cant"


def test_dimmer_districts_get_bigger_pools(conn: sqlite3.Connection) -> None:
    for light in range(6, 2, -1):
        world.apply_light_change(conn, "market", encroach(light), SYSTEM, "dark")
    sizes = [len(todays_pool(conn, "market", TUESDAY_NOON + timedelta(days=n))) for n in range(10)]
    assert min(sizes) >= 5  # Light 2: 5-9 a day


def test_bad_ideas_rejected() -> None:
    base = json.loads(DATA.joinpath("market_district.json").read_text())
    others = [json.loads(DATA.joinpath(f"{n}.json").read_text()) for n in ("languages", "calendar")]
    for bad in (
        {"when": {"locations": ["narnia"]}},
        {"when": {"parts_of_day": ["teatime"]}},
        {"when": {"tide": ["king tide"]}},
        {"when": {"moon": ["blue moon"]}},
        {"when": {"weather": ["snow"]}},
        {"kind": "boss-fight"},
        {"weight": 3},  # weights went with the table: ideas have none
    ):
        doc = json.loads(json.dumps(base))
        doc["encounter_ideas"][0].update(bad)
        with pytest.raises(ContentError):
            load_documents([doc, *others])
