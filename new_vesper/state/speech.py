"""The speech log (D81): every line spoken to a character, and what they understood."""

import sqlite3
from dataclasses import dataclass

from new_vesper.rules.languages import Heard
from new_vesper.state.validate import row_id, text

MAX_SPEAKER = 80
MAX_WORDS = 600
MAX_TONE = 80
MAX_GIST = 200


@dataclass(frozen=True)
class SpokenLine:
    id: int
    scene_id: int
    character_id: int  # who was listening
    speaker: str
    npc_id: str | None
    language_id: str | None  # None when the tag named no known language
    words: str
    tone: str | None
    gist: str | None
    heard: Heard


def _line(row: sqlite3.Row) -> SpokenLine:
    return SpokenLine(
        id=row["id"],
        scene_id=row["scene_id"],
        character_id=row["character_id"],
        speaker=row["speaker"],
        npc_id=row["npc_id"],
        language_id=row["language_id"],
        words=row["words"],
        tone=row["tone"],
        gist=row["gist"],
        heard=Heard(row["heard"]),
    )


def _optional(value: str | None, name: str, max_length: int) -> str | None:
    return None if value is None or not value.strip() else text(value, name, max_length)


def record_line(
    conn: sqlite3.Connection,
    scene_id: int,
    character_id: int,
    *,
    speaker: str,
    npc_id: str | None,
    language_id: str | None,
    words: str,
    tone: str | None,
    gist: str | None,
    heard: Heard,
) -> SpokenLine:
    cursor = conn.execute(
        "INSERT INTO speech_lines (scene_id, character_id, speaker, npc_id, language_id, words,"
        " tone, gist, heard) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row_id(scene_id, "scene id"),
            row_id(character_id, "character id"),
            text(speaker, "speaker", MAX_SPEAKER),
            npc_id,
            language_id,
            text(words, "words", MAX_WORDS),
            _optional(tone, "tone", MAX_TONE),
            _optional(gist, "gist", MAX_GIST),
            Heard(heard).value,
        ),
    )
    row = conn.execute("SELECT * FROM speech_lines WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _line(row)


def lines_in_scene(
    conn: sqlite3.Connection, scene_id: int, character_id: int, limit: int = 1000
) -> list[SpokenLine]:
    """The latest lines this character heard in a scene, oldest first."""
    rows = conn.execute(
        "SELECT * FROM speech_lines WHERE scene_id = ? AND character_id = ?"
        " ORDER BY id DESC LIMIT ?",
        (row_id(scene_id, "scene id"), row_id(character_id, "character id"), limit),
    ).fetchall()
    return [_line(row) for row in reversed(rows)]
