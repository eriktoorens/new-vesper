import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from new_vesper.city.encounters import check_for_encounter, eligible, make_stranger
from new_vesper.content.loader import Content, load_content, load_documents
from new_vesper.content.model import ContentError
from new_vesper.content.seed import seed
from new_vesper.rules.light import encroach
from new_vesper.rules.sky import TideState, tide
from new_vesper.state import world
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
    from new_vesper.state import players

    players.create_player(db, "ash", SYSTEM)
    yield db
    db.close()


def ids(conn: sqlite3.Connection, content: Content, place: str, now: datetime) -> set[str]:
    return {e.id for e in eligible(conn, content, place, now)}


def test_place_and_time_conditions(conn: sqlite3.Connection, content: Content) -> None:
    row = ids(conn, content, "tarp-row", TUESDAY_NOON)
    assert {"noodle-argument", "pickpocket", "franchise-agent"} <= row
    assert "eel-sellers" not in row and "wreck-find" not in row
    assert "lantern-parade" not in row  # not the Lantern Months
    night = datetime(2026, 9, 30, 7, tzinfo=UTC)  # 3 am city time
    assert "noodle-argument" not in ids(conn, content, "tarp-row", night)


def test_tide_conditions(conn: sqlite3.Connection, content: Content) -> None:
    moment = TUESDAY_NOON
    while tide(moment).state is not TideState.LOW:
        moment += timedelta(minutes=10)
    assert "eel-sellers" in ids(conn, content, "tidewater-stairs", moment)
    while tide(moment).state is not TideState.HIGH:
        moment += timedelta(minutes=10)
    assert "eel-sellers" not in ids(conn, content, "tidewater-stairs", moment)


def test_moon_conditions(conn: sqlite3.Connection, content: Content) -> None:
    new_moon_night = datetime(2026, 10, 11, 3, tzinfo=UTC)  # 11 pm city time, new moon
    assert "forgotten-walker" in ids(conn, content, "weighhouse", new_moon_night)
    full_moon_night = datetime(2026, 9, 27, 3, tzinfo=UTC)
    assert "forgotten-walker" not in ids(conn, content, "weighhouse", full_moon_night)


def test_district_cooldown(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")

    class Always:
        def randint(self, a: int, b: int) -> int:
            return a

    first = check_for_encounter(conn, content, char.id, "tarp-row", TUESDAY_NOON, Always(), SYSTEM)
    assert first is not None
    assert first.id not in ids(conn, content, "tarp-row", TUESDAY_NOON)
    assert first.id not in ids(conn, content, "lantern-arcade", TUESDAY_NOON)  # district-wide
    later = TUESDAY_NOON + timedelta(days=3, minutes=1)  # same time of day, 3 days on
    assert first.id in ids(conn, content, "tarp-row", later)
    assert list_events(conn, kind="encounter")[0].payload["encounter_id"] == first.id


def test_no_encounter_when_the_dice_say_no(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")

    class Never:
        def randint(self, a: int, b: int) -> int:
            return b

    assert (
        check_for_encounter(conn, content, char.id, "tarp-row", TUESDAY_NOON, Never(), SYSTEM)
        is None
    )
    assert conn.execute("SELECT COUNT(*) FROM encounters").fetchone()[0] == 0


def test_strangers_speak_the_neighborhood(content: Content) -> None:
    import random

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
    one = make_stranger(content, "tarp-row", False, "a cook", random.Random(1))
    assert one.name in content.stranger_names[one.language]


def test_stranger_is_logged(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")

    class Pickpocket:
        """Chance roll 1 (yes), then always the last option."""

        def __init__(self) -> None:
            self.first = True

        def randint(self, a: int, b: int) -> int:
            if self.first:
                self.first = False
                return 1
            return a

    enc = check_for_encounter(
        conn, content, char.id, "tarp-row", TUESDAY_NOON, Pickpocket(), SYSTEM
    )
    assert enc is not None
    row = conn.execute("SELECT stranger FROM encounters").fetchone()[0]
    if enc.stranger is not None:
        assert json.loads(row)["name"] == enc.stranger.name
    brief = enc.for_dm(content)
    assert brief["what_happens"] == enc.text


def test_fallen_district_has_no_encounters(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, location="tarp-row")
    for light in range(6, 0, -1):
        world.apply_light_change(conn, "market", encroach(light), SYSTEM, "dark")

    class Always:
        def randint(self, a: int, b: int) -> int:
            return a

    assert (
        check_for_encounter(conn, content, char.id, "tarp-row", TUESDAY_NOON, Always(), SYSTEM)
        is None
    )


def test_bad_encounters_rejected() -> None:
    base = json.loads(DATA.joinpath("market_district.json").read_text())
    for bad in (
        {"when": {"locations": ["narnia"]}},
        {"when": {"parts_of_day": ["teatime"]}},
        {"when": {"tide": ["king tide"]}},
        {"when": {"moon": ["blue moon"]}},
        {"when": {"weather": ["snow"]}},
        {"kind": "boss-fight"},
        {"weight": 0},
        {"when": {"colour": ["red"]}},
    ):
        doc = json.loads(json.dumps(base))
        doc["encounters"][0].update(bad)
        others = [
            json.loads(DATA.joinpath(f"{n}.json").read_text()) for n in ("languages", "calendar")
        ]
        with pytest.raises(ContentError):
            load_documents([doc, *others])
