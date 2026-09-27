import sqlite3
from collections.abc import Iterator

import pytest

from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.stats import Stat
from new_vesper.state import characters, players, world
from new_vesper.state.characters import Character
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM

STATS = {Stat.STEEL: 2, Stat.SLICK: 1, Stat.WIRE: 1, Stat.WEIRD: 0, Stat.HEART: -1}


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    db = open_database()
    world.add_origin(
        db, "street-born", "Street-born human", "Knows someone", ["streetwise"], SYSTEM
    )
    world.add_origin(
        db,
        "awakened-animal",
        "Awakened animal",
        "Nobody suspects a cat",
        ["no-hands", "overlooked", "animal-speech"],
        SYSTEM,
    )
    for knack_id, advanced in (
        ("read-the-crowd", False),
        ("shrine-question", False),
        ("rooftop-runner", False),
        ("iron-saint", True),
    ):
        world.add_knack(
            db,
            knack_id,
            knack_id.replace("-", " ").title(),
            "steel",
            "When you act",
            "It works",
            "It works, but",
            SYSTEM,
            advanced=advanced,
            approved=True,
        )
    world.add_knack(db, "unvetted", "Unvetted", "weird", "t", "c", "c", SYSTEM)
    world.add_region(db, "market", "The Market District", 6, SYSTEM)
    world.add_region(db, "docks", "The Docks", 4, SYSTEM)
    world.add_location(db, "spice-lane", "market", "Spice Lane", SYSTEM)
    world.add_location(db, "umbrella-shrine", "market", "Umbrella Shrine", SYSTEM, is_haven=True)
    world.add_location(db, "pier-9", "docks", "Pier 9", SYSTEM)
    players.create_player(db, "ash", SYSTEM)
    players.create_player(db, "bo", SYSTEM)
    yield db
    db.close()


def make_character(
    conn: sqlite3.Connection,
    player_id: int = 1,
    *,
    online: bool = True,
    origin: str = "street-born",
) -> Character:
    sheet = new_sheet(STATS, ("read-the-crowd", "shrine-question"))
    char = characters.create_character(
        conn,
        player_id,
        "Mira Okonkwo-Sato",
        origin,
        "Auntie Jun at the noodle cart",
        sheet,
        SYSTEM,
        location_id="spice-lane",
    )
    if online:
        char = characters.set_online(conn, char.id, True, SYSTEM)
    return char


@pytest.fixture
def mira(conn: sqlite3.Connection) -> Character:
    return make_character(conn)
