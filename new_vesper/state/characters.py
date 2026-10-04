"""Characters: persistence for the rules engine's Sheet plus narrative fields.

The rules engine computes a new Sheet; ``update_sheet`` writes it only if the
stored sheet still equals the one the change was computed from.
"""

import sqlite3
from dataclasses import dataclass
from typing import Any

from new_vesper.rules.character import Sheet, validate_name, validate_pronouns
from new_vesper.rules.currency import STARTING_GLITTER
from new_vesper.rules.errors import require_int, require_range
from new_vesper.rules.languages import COMMON_TONGUE
from new_vesper.rules.stats import Stat, validate_stats
from new_vesper.rules.tracks import TRACK_MAX
from new_vesper.state.db import atomic
from new_vesper.state.errors import StaleStateError, StateError
from new_vesper.state.events import Cause, append_event
from new_vesper.state.players import get_player
from new_vesper.state.validate import as_state_error, flag, require_row, row_id, slug, text
from new_vesper.state.world import get_knack, get_language, get_location, get_origin

_STAT_COLUMNS = tuple(stat.value for stat in Stat)


@dataclass(frozen=True)
class Character:
    id: int
    player_id: int
    name: str
    origin_id: str
    bond: str
    pronouns: str | None
    age: str | None
    appearance: str | None
    languages: tuple[str, ...]  # language ids, as chosen
    sheet: Sheet
    tags: frozenset[str]  # origin tags plus tags gained in play
    currency: int  # in glitter (D18)
    online: bool
    location_id: str | None
    version: int
    # The language they speak aloud (D80).
    speaking: str = COMMON_TONGUE
    # How they're built and how they move, in the player's words (D116).
    body: str | None = None

    @property
    def speaks(self) -> frozenset[str]:
        """Every language they understand: their own, and Registry Standard (D44)."""
        return frozenset(self.languages) | {COMMON_TONGUE}


def _check_sheet(conn: sqlite3.Connection, sheet: Sheet) -> None:
    """Refuse any sheet the rules would not allow."""
    if not isinstance(sheet, Sheet):
        raise StateError("sheet must be a rules Sheet")
    with as_state_error():
        validate_stats(sheet.stats, sheet.boosted_stat)
        require_range(sheet.harm, "harm", 0, TRACK_MAX)
        require_range(sheet.fade, "fade", 0, TRACK_MAX)
        if require_int(sheet.level, "level") < 1:
            raise StateError("level must be at least 1")
        if require_int(sheet.xp, "xp") < 0:
            raise StateError("xp must not be negative")
    for field_name, ids in (
        ("knack", sheet.knacks),
        ("advanced knack", sheet.advanced_knacks),
        ("scar", sheet.scars),
        ("origin evolution", sheet.origin_evolutions),
    ):
        if len(set(ids)) != len(ids):
            raise StateError(f"duplicate {field_name}")
        for item in ids:
            slug(item, field_name)
    for knack_id in sheet.knacks:
        knack = get_knack(conn, knack_id)
        if not knack.approved or knack.advanced:
            raise StateError(f"knack {knack_id!r} is not an approved ordinary knack")
    for knack_id in sheet.advanced_knacks:
        knack = get_knack(conn, knack_id)
        if not knack.approved or not knack.advanced:
            raise StateError(f"knack {knack_id!r} is not an approved advanced knack")


def _write_children(conn: sqlite3.Connection, character_id: int, sheet: Sheet) -> None:
    for table in ("character_knacks", "character_scars", "character_evolutions"):
        conn.execute(f"DELETE FROM {table} WHERE character_id = ?", (character_id,))
    knacks = [(k, "knack") for k in sheet.knacks] + [(k, "advanced") for k in sheet.advanced_knacks]
    conn.executemany(
        "INSERT INTO character_knacks (character_id, knack_id, kind, position) VALUES (?, ?, ?, ?)",
        [(character_id, k, kind, i) for i, (k, kind) in enumerate(knacks)],
    )
    conn.executemany(
        "INSERT INTO character_scars (character_id, scar_id, position) VALUES (?, ?, ?)",
        [(character_id, s, i) for i, s in enumerate(sheet.scars)],
    )
    conn.executemany(
        "INSERT INTO character_evolutions (character_id, evolution_id, position) VALUES (?, ?, ?)",
        [(character_id, e, i) for i, e in enumerate(sheet.origin_evolutions)],
    )


def _check_languages(conn: sqlite3.Connection, languages: object) -> tuple[str, ...]:
    if not isinstance(languages, tuple):
        raise StateError("languages must be a tuple of language ids")
    ids = tuple(slug(lang, "language") for lang in languages)
    if len(set(ids)) != len(ids):
        raise StateError("a language is listed twice")
    for lang in ids:
        get_language(conn, lang)
    return ids


def _write_languages(conn: sqlite3.Connection, character_id: int, ids: tuple[str, ...]) -> None:
    conn.execute("DELETE FROM character_languages WHERE character_id = ?", (character_id,))
    conn.executemany(
        "INSERT INTO character_languages (character_id, language_id) VALUES (?, ?)",
        [(character_id, lang) for lang in ids],
    )


def _sheet_columns(sheet: Sheet) -> dict[str, Any]:
    return {
        "level": sheet.level,
        "xp": sheet.xp,
        "harm": sheet.harm,
        "fade": sheet.fade,
        **{stat.value: sheet.stats[stat] for stat in Stat},
        "boosted_stat": sheet.boosted_stat.value if sheet.boosted_stat else None,
        "fallen": int(sheet.fallen),
        "slipped": int(sheet.slipped),
    }


def create_character(
    conn: sqlite3.Connection,
    player_id: int,
    name: str,
    origin_id: str,
    bond: str,
    sheet: Sheet,
    cause: Cause,
    *,
    location_id: str | None = None,
    pronouns: str | None = None,
    age: str | None = None,
    appearance: str | None = None,
    languages: tuple[str, ...] = (),
    body: str | None = None,
) -> Character:
    """Store a new character. Build ``sheet`` with ``rules.character.create_character``."""
    player = get_player(conn, player_id)
    origin = get_origin(conn, origin_id)
    with as_state_error():
        clean_name = validate_name(name)
        clean_pronouns = None if pronouns is None else validate_pronouns(pronouns)
    clean_bond = text(bond, "bond", 200).strip()
    clean_age = None if age is None else text(age, "age", 60).strip()
    clean_look = None if appearance is None else text(appearance, "appearance", 300).strip()
    clean_body = None if body is None else text(body, "body", 200).strip()
    spoken = _check_languages(conn, languages)
    if location_id is not None:
        location_id = get_location(conn, location_id).id
    _check_sheet(conn, sheet)
    columns = {
        "player_id": player.id,
        "name": clean_name,
        "origin_id": origin.id,
        "bond": clean_bond,
        "pronouns": clean_pronouns,
        "age": clean_age,
        "appearance": clean_look,
        "body": clean_body,
        "location_id": location_id,
        "currency": STARTING_GLITTER,
        **_sheet_columns(sheet),
    }
    with atomic(conn), as_state_error():
        cursor = conn.execute(
            f"INSERT INTO characters ({', '.join(columns)})"
            f" VALUES ({', '.join('?' for _ in columns)})",
            tuple(columns.values()),
        )
        character_id = int(cursor.lastrowid or 0)
        _write_children(conn, character_id, sheet)
        _write_languages(conn, character_id, spoken)
        append_event(
            conn,
            "character_created",
            cause,
            {"origin_id": origin.id, "knacks": list(sheet.knacks)},
            character_id=character_id,
        )
    return get_character(conn, character_id)


def _ids(conn: sqlite3.Connection, sql: str, character_id: int) -> tuple[str, ...]:
    return tuple(row[0] for row in conn.execute(sql, (character_id,)))


def get_character(conn: sqlite3.Connection, character_id: int) -> Character:
    cid = row_id(character_id, "character id")
    row = require_row(
        conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone(), "character", cid
    )
    knack_sql = (
        "SELECT knack_id FROM character_knacks WHERE character_id = ? AND kind = '{}'"
        " ORDER BY position"
    )
    sheet = Sheet(
        stats={stat: row[stat.value] for stat in Stat},
        knacks=_ids(conn, knack_sql.format("knack"), cid),
        level=row["level"],
        xp=row["xp"],
        harm=row["harm"],
        fade=row["fade"],
        scars=_ids(
            conn,
            "SELECT scar_id FROM character_scars WHERE character_id = ? ORDER BY position",
            cid,
        ),
        advanced_knacks=_ids(conn, knack_sql.format("advanced"), cid),
        origin_evolutions=_ids(
            conn,
            "SELECT evolution_id FROM character_evolutions WHERE character_id = ?"
            " ORDER BY position",
            cid,
        ),
        boosted_stat=Stat(row["boosted_stat"]) if row["boosted_stat"] else None,
        fallen=bool(row["fallen"]),
        slipped=bool(row["slipped"]),
    )
    return Character(
        id=row["id"],
        player_id=row["player_id"],
        name=row["name"],
        origin_id=row["origin_id"],
        bond=row["bond"],
        pronouns=row["pronouns"],
        age=row["age"],
        appearance=row["appearance"],
        body=row["body"],
        languages=_ids(
            conn,
            "SELECT language_id FROM character_languages WHERE character_id = ? ORDER BY rowid",
            cid,
        ),
        sheet=sheet,
        tags=get_origin(conn, row["origin_id"]).tags
        | frozenset(
            t[0]
            for t in conn.execute("SELECT tag FROM character_tags WHERE character_id = ?", (cid,))
        ),
        currency=row["currency"],
        online=bool(row["online"]),
        location_id=row["location_id"],
        version=row["version"],
        speaking=row["speaking"] or COMMON_TONGUE,
    )


def _diff(before: Sheet, after: Sheet) -> dict[str, Any]:
    old, new = _sheet_columns(before), _sheet_columns(after)
    changes: dict[str, Any] = {k: [old[k], new[k]] for k in old if old[k] != new[k]}
    for attr in ("knacks", "advanced_knacks", "scars", "origin_evolutions"):
        if getattr(before, attr) != getattr(after, attr):
            changes[attr] = [list(getattr(before, attr)), list(getattr(after, attr))]
    return changes


def update_sheet(
    conn: sqlite3.Connection,
    character_id: int,
    before: Sheet,
    after: Sheet,
    cause: Cause,
    reason: str,
) -> Character:
    """Write a sheet the rules engine computed from ``before``.

    Refused if the stored sheet no longer equals ``before`` (someone else
    wrote first), if ``after`` breaks the rules, if a fallen character would
    change, or if an offline character's Harm or Fade would change.
    """
    why = text(reason, "reason", 300)
    if not isinstance(before, Sheet) or not isinstance(after, Sheet):
        raise StateError("sheets must be rules Sheets")
    with atomic(conn):
        current = get_character(conn, character_id)
        if current.sheet != before:
            raise StaleStateError("the character changed since it was read")
        if before == after:
            return current
        if before.fallen:
            raise StateError("this character has fallen")
        tracks_changed = (before.harm, before.fade) != (after.harm, after.fade)
        if tracks_changed and not current.online:
            raise StateError("offline characters cannot be harmed and their tracks don't change")
        _check_sheet(conn, after)
        columns = _sheet_columns(after)
        with as_state_error():
            cursor = conn.execute(
                f"UPDATE characters SET {', '.join(f'{k} = ?' for k in columns)},"
                " version = version + 1 WHERE id = ? AND version = ?",
                (*columns.values(), current.id, current.version),
            )
            if cursor.rowcount != 1:
                raise StaleStateError("the character changed since it was read")
            _write_children(conn, current.id, after)
        append_event(
            conn,
            "sheet_changed",
            cause,
            {"changes": _diff(before, after), "reason": why},
            character_id=current.id,
        )
    return get_character(conn, current.id)


def _update_field(
    conn: sqlite3.Connection,
    character: Character,
    column: str,
    value: object,
    kind: str,
    cause: Cause,
    payload: dict[str, Any],
) -> Character:
    with atomic(conn), as_state_error():
        conn.execute(
            f"UPDATE characters SET {column} = ?, version = version + 1 WHERE id = ?",
            (value, character.id),
        )
        append_event(conn, kind, cause, payload, character_id=character.id)
    return get_character(conn, character.id)


def set_online(
    conn: sqlite3.Connection, character_id: int, online: bool, cause: Cause
) -> Character:
    character = get_character(conn, character_id)
    value = flag(online, "online")
    return _update_field(
        conn, character, "online", int(value), "presence_changed", cause, {"online": value}
    )


def move_character(
    conn: sqlite3.Connection, character_id: int, location_id: str | None, cause: Cause
) -> Character:
    character = get_character(conn, character_id)
    if character.sheet.fallen:
        raise StateError("this character has fallen")
    target = None if location_id is None else get_location(conn, location_id).id
    return _update_field(
        conn,
        character,
        "location_id",
        target,
        "character_moved",
        cause,
        {"from": character.location_id, "to": target},
    )


def adjust_currency(
    conn: sqlite3.Connection, character_id: int, delta: int, cause: Cause, reason: str
) -> Character:
    """Add or remove currency. A balance never goes below zero."""
    why = text(reason, "reason", 300)
    with as_state_error():
        amount = require_int(delta, "currency change")
    if amount == 0:
        raise StateError("currency change must not be zero")
    with atomic(conn):
        character = get_character(conn, character_id)
        after = character.currency + amount
        if after < 0:
            raise StateError(f"not enough currency: have {character.currency}, need {-amount}")
        return _update_field(
            conn,
            character,
            "currency",
            after,
            "currency_changed",
            cause,
            {"before": character.currency, "after": after, "reason": why},
        )


def add_character_tag(
    conn: sqlite3.Connection, character_id: int, tag: str, cause: Cause
) -> Character:
    """Give a character a tag gained in play. Adding a tag it already has is a no-op."""
    character = get_character(conn, character_id)
    name = slug(tag, "tag")
    if name in character.tags:
        return character
    with atomic(conn):
        conn.execute(
            "INSERT INTO character_tags (character_id, tag) VALUES (?, ?)", (character.id, name)
        )
        append_event(conn, "tag_gained", cause, {"tag": name}, character_id=character.id)
    return get_character(conn, character.id)


def characters_of(conn: sqlite3.Connection, player_id: int) -> list[Character]:
    """A player's characters, oldest first."""
    pid = get_player(conn, player_id).id
    rows = conn.execute("SELECT id FROM characters WHERE player_id = ? ORDER BY id", (pid,))
    return [get_character(conn, row[0]) for row in rows]


def set_pronouns(
    conn: sqlite3.Connection, character_id: int, pronouns: str, cause: Cause
) -> Character:
    """Set or change a character's pronouns."""
    character = get_character(conn, character_id)
    with as_state_error():
        value = validate_pronouns(pronouns)
    return _update_field(
        conn, character, "pronouns", value, "pronouns_set", cause, {"pronouns": value}
    )


def set_body(conn: sqlite3.Connection, character_id: int, body: str, cause: Cause) -> Character:
    """Set or change how a character is built and moves, in the player's words (D116)."""
    character = get_character(conn, character_id)
    value = text(body, "body", 200).strip()
    return _update_field(conn, character, "body", value, "body_set", cause, {"body": value})


def rename_character(
    conn: sqlite3.Connection, character_id: int, name: str, cause: Cause
) -> Character:
    """Change a character's name (D107). The event log keeps the old one."""
    character = get_character(conn, character_id)
    with as_state_error():
        value = validate_name(name)
    if value == character.name:
        raise StateError(f"{character.name} is already called that")
    return _update_field(
        conn, character, "name", value, "renamed", cause, {"from": character.name, "to": value}
    )


def set_details(
    conn: sqlite3.Connection,
    character_id: int,
    cause: Cause,
    *,
    age: str,
    appearance: str,
    languages: tuple[str, ...],
) -> Character:
    """Fill in age, appearance and languages, e.g. for a character made before they existed."""
    character = get_character(conn, character_id)
    clean_age = text(age, "age", 60).strip()
    clean_look = text(appearance, "appearance", 300).strip()
    spoken = _check_languages(conn, languages)
    with atomic(conn), as_state_error():
        conn.execute(
            "UPDATE characters SET age = ?, appearance = ?, version = version + 1 WHERE id = ?",
            (clean_age, clean_look, character.id),
        )
        _write_languages(conn, character.id, spoken)
        append_event(
            conn, "details_set", cause, {"languages": list(spoken)}, character_id=character.id
        )
    return get_character(conn, character.id)


def set_speaking(
    conn: sqlite3.Connection, character_id: int, language_id: str, cause: Cause
) -> Character:
    """Choose the language the character speaks aloud: one they know (D80)."""
    character = get_character(conn, character_id)
    lang = slug(language_id, "language")
    if lang not in character.speaks:
        raise StateError(f"{character.name} doesn't speak {lang!r}")
    return _update_field(
        conn, character, "speaking", lang, "speaking_changed", cause, {"language": lang}
    )


def played_locations(conn: sqlite3.Connection, character_id: int) -> frozenset[str]:
    """Places this character has played a scene in."""
    rows = conn.execute(
        "SELECT DISTINCT s.location_id FROM scene_participants p"
        " JOIN scenes s ON s.id = p.scene_id"
        " WHERE p.character_id = ? AND s.location_id IS NOT NULL",
        (row_id(character_id, "character id"),),
    )
    return frozenset(row[0] for row in rows)


def visited_locations(conn: sqlite3.Connection, character_id: int) -> frozenset[str]:
    """Places this character has played a scene in, plus where they are now."""
    character = get_character(conn, character_id)
    here = {character.location_id} if character.location_id else set()
    return played_locations(conn, character.id) | here
