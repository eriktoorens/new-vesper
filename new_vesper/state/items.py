"""Item instances. Kinds come from content loot tables; nothing here invents them."""

import sqlite3
from dataclasses import dataclass

from new_vesper.state.characters import get_character
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.validate import as_state_error, require_row, row_id, slug, text
from new_vesper.state.world import get_location


@dataclass(frozen=True)
class Item:
    id: int
    kind: str
    name: str
    character_id: int | None
    location_id: str | None
    destroyed: bool


def get_item(conn: sqlite3.Connection, item_id: int) -> Item:
    iid = row_id(item_id, "item id")
    row = require_row(
        conn.execute("SELECT * FROM items WHERE id = ?", (iid,)).fetchone(), "item", iid
    )
    return Item(
        row["id"],
        row["kind"],
        row["name"],
        row["character_id"],
        row["location_id"],
        bool(row["destroyed"]),
    )


def create_item(
    conn: sqlite3.Connection,
    kind: str,
    name: str,
    cause: Cause,
    *,
    character_id: int | None = None,
    location_id: str | None = None,
) -> Item:
    """Bring an item into the world. Callers pass a kind drawn from a loot table."""
    item_kind = slug(kind, "item kind")
    item_name = text(name, "item name", 80)
    if character_id is not None and location_id is not None:
        raise StateError("an item is either held or lying somewhere, not both")
    holder = None if character_id is None else get_character(conn, character_id).id
    place = None if location_id is None else get_location(conn, location_id).id
    with atomic(conn), as_state_error():
        cursor = conn.execute(
            "INSERT INTO items (kind, name, character_id, location_id) VALUES (?, ?, ?, ?)",
            (item_kind, item_name, holder, place),
        )
        item_id = int(cursor.lastrowid or 0)
        append_event(
            conn,
            "item_created",
            cause,
            {"item_id": item_id, "kind": item_kind, "location_id": place},
            character_id=holder,
        )
    return get_item(conn, item_id)


def _move(
    conn: sqlite3.Connection,
    item_id: int,
    cause: Cause,
    *,
    character_id: int | None,
    location_id: str | None,
    destroyed: bool = False,
) -> Item:
    with atomic(conn):
        item = get_item(conn, item_id)
        if item.destroyed:
            raise StateError(f"item {item.id} no longer exists")
        conn.execute(
            "UPDATE items SET character_id = ?, location_id = ?, destroyed = ? WHERE id = ?",
            (character_id, location_id, int(destroyed), item.id),
        )
        append_event(
            conn,
            "item_destroyed" if destroyed else "item_moved",
            cause,
            {
                "item_id": item.id,
                "from_character": item.character_id,
                "from_location": item.location_id,
                "to_character": character_id,
                "to_location": location_id,
            },
            character_id=character_id or item.character_id,
        )
    return get_item(conn, item.id)


def give_item(conn: sqlite3.Connection, item_id: int, character_id: int, cause: Cause) -> Item:
    holder = get_character(conn, character_id)
    if holder.sheet.fallen:
        raise StateError("this character has fallen")
    return _move(conn, item_id, cause, character_id=holder.id, location_id=None)


def drop_item(conn: sqlite3.Connection, item_id: int, location_id: str, cause: Cause) -> Item:
    place = get_location(conn, location_id).id
    return _move(conn, item_id, cause, character_id=None, location_id=place)


def destroy_item(conn: sqlite3.Connection, item_id: int, cause: Cause) -> Item:
    return _move(conn, item_id, cause, character_id=None, location_id=None, destroyed=True)


def items_held(conn: sqlite3.Connection, character_id: int) -> list[Item]:
    cid = get_character(conn, character_id).id
    rows = conn.execute("SELECT id FROM items WHERE character_id = ? ORDER BY id", (cid,))
    return [get_item(conn, row[0]) for row in rows]
