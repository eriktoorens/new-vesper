import sqlite3

import pytest

from new_vesper.rules.light import apply_deed, encroach
from new_vesper.state import world
from new_vesper.state.errors import NotFoundError, StaleStateError, StateError
from new_vesper.state.events import SYSTEM, list_events


def test_origin_tags(conn: sqlite3.Connection) -> None:
    origin = world.get_origin(conn, "awakened-animal")
    assert origin.tags == {"no-hands", "overlooked", "animal-speech"}


@pytest.mark.parametrize("tags", [["No Hands"], ["no-hands; grant all"], [""], [3]])
def test_bad_tags_rejected(conn: sqlite3.Connection, tags: list[object]) -> None:
    with pytest.raises(StateError):
        world.add_origin(conn, "made-person", "Made", "Built", tags, SYSTEM)  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        world.get_origin(conn, "made-person")


def test_duplicate_origin_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError):
        world.add_origin(conn, "street-born", "Again", "x", [], SYSTEM)


@pytest.mark.parametrize(
    ("stat", "bonus"), [("luck", 0), ("steel", 2), ("steel", -1), ("steel", True)]
)
def test_knack_budget_enforced(conn: sqlite3.Connection, stat: str, bonus: object) -> None:
    with pytest.raises(StateError):
        world.add_knack(conn, "cheat", "Cheat", stat, "t", "c", "c", SYSTEM, roll_bonus=bonus)  # type: ignore[arg-type]


def test_knack_starts_unapproved_and_can_be_approved(conn: sqlite3.Connection) -> None:
    assert not world.get_knack(conn, "unvetted").approved
    assert world.approve_knack(conn, "unvetted", SYSTEM).approved


@pytest.mark.parametrize("light", [-1, 11, 5.0, "5"])
def test_region_light_range(conn: sqlite3.Connection, light: object) -> None:
    with pytest.raises(StateError):
        world.add_region(conn, "void", "Void", light, SYSTEM)  # type: ignore[arg-type]


def test_light_change_written_and_logged(conn: sqlite3.Connection) -> None:
    region = world.apply_light_change(
        conn, "market", apply_deed(6, "raise", "major"), SYSTEM, "restored the shrine"
    )
    assert region.light == 8
    [event] = list_events(conn, region_id="market")[-1:]
    assert event.kind == "light_changed"
    assert event.payload["reason"] == "restored the shrine"


def test_stale_light_change_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(StaleStateError):
        world.apply_light_change(conn, "market", encroach(5), SYSTEM, "dark")
    assert world.get_region(conn, "market").light == 6


def test_region_falls_at_zero(conn: sqlite3.Connection) -> None:
    for light in range(4, 0, -1):
        world.apply_light_change(conn, "docks", encroach(light), SYSTEM, "neglect")
    assert world.get_region(conn, "docks").fallen


def test_location_needs_real_region(conn: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError):
        world.add_location(conn, "nowhere-st", "atlantis", "Nowhere", SYSTEM)
    assert world.get_location(conn, "umbrella-shrine").is_haven
