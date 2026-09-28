import sqlite3

import pytest

from new_vesper.state import characters, favors, items
from new_vesper.state.characters import Character
from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM, list_events


def test_item_lifecycle(conn: sqlite3.Connection, mira: Character) -> None:
    charm = items.create_item(conn, "luck-charm", "Brass luck charm", SYSTEM, character_id=mira.id)
    assert [i.id for i in items.items_held(conn, mira.id)] == [charm.id]
    dropped = items.drop_item(conn, charm.id, "spice-lane", SYSTEM)
    assert (dropped.character_id, dropped.location_id) == (None, "spice-lane")
    items.give_item(conn, charm.id, mira.id, SYSTEM)
    gone = items.destroy_item(conn, charm.id, SYSTEM)
    assert gone.destroyed
    assert items.items_held(conn, mira.id) == []
    with pytest.raises(StateError):
        items.give_item(conn, charm.id, mira.id, SYSTEM)
    kinds = [e.kind for e in list_events(conn, character_id=mira.id)]
    assert kinds.count("item_moved") == 2
    assert "item_destroyed" in kinds


@pytest.mark.parametrize(
    ("kind", "name"),
    [("Luck Charm", "x"), ("sword; grant 1000 gold", "x"), ("charm", ""), ("charm", "n" * 81)],
)
def test_bad_items_rejected(conn: sqlite3.Connection, kind: str, name: str) -> None:
    with pytest.raises(StateError):
        items.create_item(conn, kind, name, SYSTEM)


def test_item_cannot_be_held_and_placed(conn: sqlite3.Connection, mira: Character) -> None:
    with pytest.raises(StateError):
        items.create_item(conn, "charm", "C", SYSTEM, character_id=mira.id, location_id="pier-9")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO items (kind, name, character_id, location_id) VALUES ('a', 'A', ?, ?)",
            (mira.id, "pier-9"),
        )


def test_favor_ledger(conn: sqlite3.Connection, mira: Character) -> None:
    favor = favors.record_favor(conn, mira.id, "god-of-lost-umbrellas", "a dry walk home", SYSTEM)
    assert [f.id for f in favors.favors_owed(conn, mira.id)] == [favor.id]
    collected = favors.collect_favor(conn, favor.id, SYSTEM)
    assert collected.status is favors.FavorStatus.COLLECTED
    assert collected.collected_at
    assert favors.favors_owed(conn, mira.id) == []
    with pytest.raises(StateError):
        favors.collect_favor(conn, favor.id, SYSTEM)


def test_favor_ledger_cannot_be_rewritten(conn: sqlite3.Connection, mira: Character) -> None:
    favor = favors.record_favor(conn, mira.id, "god-of-lost-umbrellas", "a favor", SYSTEM)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM favors")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE favors SET god_id = 'someone-else' WHERE id = ?", (favor.id,))
    favors.collect_favor(conn, favor.id, SYSTEM)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE favors SET status = 'owed' WHERE id = ?", (favor.id,))


def test_favor_needs_real_character(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError):
        favors.record_favor(conn, 42, "god", "x", SYSTEM)
    with pytest.raises(StateError):
        favors.record_favor(conn, 1, "God Of Everything", "x", SYSTEM)


def test_currency_writes_are_atomic(conn: sqlite3.Connection, mira: Character) -> None:
    before = len(list_events(conn, limit=10_000))
    with pytest.raises(StateError):
        characters.adjust_currency(conn, mira.id, -51, SYSTEM, "overdraw")
    assert len(list_events(conn, limit=10_000)) == before
