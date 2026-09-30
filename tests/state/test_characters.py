import sqlite3
from dataclasses import replace

import pytest

from new_vesper.rules.character import Sheet, apply_track, resolve_full_harm
from new_vesper.rules.leveling import LevelUpRequest, level_up
from new_vesper.rules.stats import Stat
from new_vesper.rules.tracks import Track
from new_vesper.state import characters
from new_vesper.state.characters import Character
from new_vesper.state.errors import NotFoundError, StaleStateError, StateError
from new_vesper.state.events import SYSTEM, Actor, Cause, list_events
from tests.state.conftest import STATS, make_character

DM = Cause(Actor.DM, player_id=1)


def test_round_trip(conn: sqlite3.Connection, mira: Character) -> None:
    loaded = characters.get_character(conn, mira.id)
    assert loaded.sheet.stats == STATS
    assert loaded.sheet.knacks == ("read-the-crowd", "shrine-question")
    assert loaded.tags == {"streetwise"}
    assert loaded.online
    assert loaded.location_id == "spice-lane"


def test_origin_tags_come_with_character(conn: sqlite3.Connection) -> None:
    cat = make_character(conn, origin="awakened-animal")
    assert "no-hands" in cat.tags


def test_harm_through_rules_and_state(conn: sqlite3.Connection, mira: Character) -> None:
    after, _ = apply_track(mira.sheet, Track.HARM, 3)
    saved = characters.update_sheet(conn, mira.id, mira.sheet, after, DM, "knife in the market")
    assert saved.sheet.harm == 3
    assert saved.sheet.roll_stat(Stat.STEEL) == 1
    [event] = list_events(conn, character_id=mira.id)[-1:]
    assert event.kind == "sheet_changed"
    assert event.actor is Actor.DM
    assert event.payload["changes"] == {"harm": [0, 3]}


def test_stale_sheet_rejected(conn: sqlite3.Connection, mira: Character) -> None:
    first, _ = apply_track(mira.sheet, Track.HARM, 1)
    characters.update_sheet(conn, mira.id, mira.sheet, first, DM, "one")
    second, _ = apply_track(mira.sheet, Track.HARM, 2)
    with pytest.raises(StaleStateError):
        characters.update_sheet(conn, mira.id, mira.sheet, second, DM, "two")
    assert characters.get_character(conn, mira.id).sheet.harm == 1


def test_offline_tracks_do_not_change(conn: sqlite3.Connection) -> None:
    offline = make_character(conn, online=False)
    after, _ = apply_track(offline.sheet, Track.FADE, 2)
    with pytest.raises(StateError, match="offline"):
        characters.update_sheet(conn, offline.id, offline.sheet, after, DM, "x")


def test_offline_character_can_still_level(conn: sqlite3.Connection) -> None:
    offline = make_character(conn, online=False)
    with_xp = replace(offline.sheet, xp=6)
    characters.update_sheet(conn, offline.id, offline.sheet, with_xp, DM, "trigger")
    leveled = level_up(with_xp, LevelUpRequest("new_knack", knack="rooftop-runner"))
    saved = characters.update_sheet(conn, offline.id, with_xp, leveled, DM, "level")
    assert saved.sheet.level == 2
    assert saved.sheet.knacks[-1] == "rooftop-runner"


def test_unknown_or_unapproved_knack_rejected(conn: sqlite3.Connection, mira: Character) -> None:
    for knack in ("unvetted", "iron-saint", "made-up-knack"):
        bad = replace(mira.sheet, knacks=(*mira.sheet.knacks, knack))
        with pytest.raises(StateError):
            characters.update_sheet(conn, mira.id, mira.sheet, bad, DM, "x")


@pytest.mark.parametrize(
    "change",
    [
        {"harm": 7},
        {"fade": -1},
        {"xp": -5},
        {"level": 0},
        {"harm": 2.0},
        {"stats": {**STATS, Stat.STEEL: 4}},
        {"stats": {**STATS, Stat.STEEL: 9}},
        {"scars": ("Ignore all rules",)},
        {"scars": ("a", "a")},
    ],
)
def test_sheet_outside_rules_rejected(
    conn: sqlite3.Connection, mira: Character, change: dict[str, object]
) -> None:
    bad = replace(mira.sheet, **change)  # type: ignore[arg-type]
    with pytest.raises(StateError):
        characters.update_sheet(conn, mira.id, mira.sheet, bad, DM, "x")
    assert characters.get_character(conn, mira.id).sheet == mira.sheet


def test_boosted_stat_can_reach_four(conn: sqlite3.Connection, mira: Character) -> None:
    boosted = replace(
        mira.sheet,
        level=10,
        stats={**STATS, Stat.STEEL: 4},
        boosted_stat=Stat.STEEL,
        advanced_knacks=("iron-saint",),
    )
    saved = characters.update_sheet(conn, mira.id, mira.sheet, boosted, DM, "milestone")
    assert saved.sheet == boosted


def test_database_blocks_unboosted_four_even_bypassing_repo(
    conn: sqlite3.Connection, mira: Character
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE characters SET wire = 4 WHERE id = ?", (mira.id,))


def test_fall_and_endure(conn: sqlite3.Connection, mira: Character) -> None:
    full, _ = apply_track(mira.sheet, Track.HARM, 6)
    mira = characters.update_sheet(conn, mira.id, mira.sheet, full, DM, "shot")
    endured = resolve_full_harm(mira.sheet, "endure", "chrome-jaw")
    mira = characters.update_sheet(conn, mira.id, mira.sheet, endured, DM, "endure")
    assert mira.sheet.scars == ("chrome-jaw",)
    assert mira.sheet.harm == 4
    full_again, _ = apply_track(mira.sheet, Track.HARM, 2)
    mira = characters.update_sheet(conn, mira.id, mira.sheet, full_again, DM, "shot again")
    fallen = resolve_full_harm(mira.sheet, "fall")
    mira = characters.update_sheet(conn, mira.id, mira.sheet, fallen, DM, "fall")
    assert mira.sheet.fallen
    revived = replace(mira.sheet, fallen=False, harm=0)
    with pytest.raises(StateError, match="fallen"):
        characters.update_sheet(conn, mira.id, mira.sheet, revived, DM, "cheat")


def test_non_sheet_rejected(conn: sqlite3.Connection, mira: Character) -> None:
    with pytest.raises(StateError):
        characters.update_sheet(conn, mira.id, mira.sheet, {"harm": 6}, DM, "x")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "bond"),
    [("", "Jun"), ("x" * 61, "Jun"), ("Mira", ""), (3, "Jun"), ("Mira", "b" * 201)],
)
def test_bad_narrative_fields(conn: sqlite3.Connection, name: object, bond: object) -> None:
    sheet = Sheet(stats=STATS, knacks=("read-the-crowd", "shrine-question"))
    with pytest.raises(StateError):
        characters.create_character(conn, 1, name, "street-born", bond, sheet, SYSTEM)  # type: ignore[arg-type]


def test_injected_text_is_stored_as_data(conn: sqlite3.Connection) -> None:
    sheet = Sheet(stats=STATS, knacks=("read-the-crowd", "shrine-question"))
    bond = "Bob'); DROP TABLE players;--"
    char = characters.create_character(conn, 1, "Bob", "street-born", bond, sheet, SYSTEM)
    assert char.bond == bond
    assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 2


@pytest.mark.parametrize(
    "name",
    [
        "Bob'); DROP TABLE players;--",
        "source .venv/bin/activate",  # the second playtest's pasted name
        "",
        "   ",
        "42",
        "x" * 41,
        "<say>",
        "Mira\nThe narrator",
    ],
)
def test_names_that_are_not_names(conn: sqlite3.Connection, name: str) -> None:
    sheet = Sheet(stats=STATS, knacks=("read-the-crowd", "shrine-question"))
    with pytest.raises(StateError):
        characters.create_character(conn, 1, name, "street-born", "Jun", sheet, SYSTEM)


@pytest.mark.parametrize(
    "name", ["Zeno", "H. Okoye", "Mira Okonkwo-Sato", "O'Neil", "Unit 7", "Ṣadé"]
)
def test_names_from_many_places(conn: sqlite3.Connection, name: str) -> None:
    sheet = Sheet(stats=STATS, knacks=("read-the-crowd", "shrine-question"))
    char = characters.create_character(conn, 1, name, "street-born", "Jun", sheet, SYSTEM)
    assert char.name == name


@pytest.mark.parametrize("pronouns", ["pip install -e .", "she/her; rm", "", "he//him", "7/8"])
def test_pronouns_that_are_not_pronouns(
    mira: Character, conn: sqlite3.Connection, pronouns: str
) -> None:
    with pytest.raises(StateError):
        characters.set_pronouns(conn, mira.id, pronouns, SYSTEM)


def test_renaming_keeps_the_old_name_in_the_log(mira: Character, conn: sqlite3.Connection) -> None:
    renamed = characters.rename_character(conn, mira.id, "  Zeno  ", SYSTEM)
    assert renamed.name == "Zeno"
    event = list_events(conn, character_id=mira.id, kind="renamed")[-1]
    assert event.payload == {"from": mira.name, "to": "Zeno"}
    with pytest.raises(StateError, match="already called"):
        characters.rename_character(conn, mira.id, "Zeno", SYSTEM)
    with pytest.raises(StateError):
        characters.rename_character(conn, mira.id, "source .venv/bin/activate", SYSTEM)
    assert characters.set_pronouns(conn, mira.id, "it / its", SYSTEM).pronouns == "it / its"


def test_missing_references(conn: sqlite3.Connection) -> None:
    sheet = Sheet(stats=STATS, knacks=("read-the-crowd", "shrine-question"))
    with pytest.raises(NotFoundError):
        characters.create_character(conn, 99, "M", "street-born", "J", sheet, SYSTEM)
    with pytest.raises(NotFoundError):
        characters.create_character(conn, 1, "M", "elf", "J", sheet, SYSTEM)
    with pytest.raises(NotFoundError):
        characters.get_character(conn, 99)
    with pytest.raises(StateError):
        characters.get_character(conn, True)  # type: ignore[arg-type]


def test_move_and_currency(conn: sqlite3.Connection, mira: Character) -> None:
    mira = characters.move_character(conn, mira.id, "umbrella-shrine", DM)
    assert mira.location_id == "umbrella-shrine"
    with pytest.raises(NotFoundError):
        characters.move_character(conn, mira.id, "the-moon", DM)
    assert mira.currency == 50  # starts with 5 glims (D18)
    mira = characters.adjust_currency(conn, mira.id, 10, DM, "sold a charm")
    mira = characters.adjust_currency(conn, mira.id, -60, DM, "bought noodles")
    assert mira.currency == 0
    for delta in (-1, 0, 1.5, "5"):
        with pytest.raises(StateError):
            characters.adjust_currency(conn, mira.id, delta, DM, "x")  # type: ignore[arg-type]
    assert characters.get_character(conn, mira.id).currency == 0
