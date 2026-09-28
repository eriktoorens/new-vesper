"""Layer 2: character details, languages, maps and art."""

import sqlite3
from typing import Any

import pytest

from new_vesper.content.languages import starting_languages
from new_vesper.content.loader import Content
from new_vesper.content.maps import render_map
from new_vesper.content.model import ContentError
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.session import PlaySession
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.state import characters
from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM
from tests.dm.conftest import DESIGN_TEXT, STATS, SeqRng, StubClient, make_character, say


def test_starting_languages(content: Content) -> None:
    assert starting_languages(content, "street-born", "arabic", "protocol") == (
        "registry-standard",
        "arabic",
        "protocol",
    )
    assert starting_languages(content, "enclave-raised", "protocol", "hindi")[1] == "protocol"


@pytest.mark.parametrize(
    ("origin", "pick", "extra"),
    [
        ("street-born", "protocol", "hindi"),  # not a market language
        ("enclave-raised", "hindi", "wolof"),  # enclave gives Protocol, fixed
        ("street-born", "arabic", "arabic"),  # already spoken
        ("street-born", "arabic", "registry-standard"),
        ("street-born", "arabic", "elvish"),
        ("elf", "arabic", "hindi"),
    ],
)
def test_bad_language_choices(content: Content, origin: str, pick: str, extra: str) -> None:
    with pytest.raises(ContentError):
        starting_languages(content, origin, pick, extra)


def test_map_fog_and_you_are_here(content: Content) -> None:
    rows = render_map(content, "market", "tarp-row", frozenset({"tarp-row", "weighhouse"}))
    drawn = "\n".join(rows)
    assert "[@]" in drawn and "[2]" not in drawn
    assert "  [5] The Old Weighhouse (weighhouse)" in rows
    assert "  [1] ???" in rows
    assert all(len(row) <= 72 for row in rows[:-7])


def test_details_are_stored_and_validated(conn: sqlite3.Connection) -> None:
    sheet = new_sheet(STATS, ("rooftop-runner", "read-the-crowd"))
    kw: dict[str, Any] = {
        "location_id": "tarp-row",
        "pronouns": "she/her",
        "age": "thirties",
        "appearance": "Tall",
        "languages": ("registry-standard", "wolof"),
    }
    char = characters.create_character(conn, 1, "Mira", "street-born", "Jun", sheet, SYSTEM, **kw)
    assert char.languages == ("registry-standard", "wolof")
    for bad in (("klingon",), ("wolof", "wolof"), ["wolof"], ("Wolof; DROP TABLE",)):
        with pytest.raises(StateError):
            characters.create_character(
                conn, 1, "X", "street-born", "Y", sheet, SYSTEM, **{**kw, "languages": bad}
            )
    with pytest.raises(StateError):
        characters.create_character(
            conn, 1, "X", "street-born", "Y", sheet, SYSTEM, **{**kw, "appearance": "a" * 301}
        )


def test_legacy_characters_can_fill_in_details(conn: sqlite3.Connection) -> None:
    char = make_character(conn)
    assert (char.age, char.appearance, char.languages) == (None, None, ())
    char = characters.set_details(
        conn,
        char.id,
        SYSTEM,
        age="twenties",
        appearance="Quick hands",
        languages=("registry-standard",),
    )
    assert char.age == "twenties"


def test_the_dm_sees_details_and_neighborhood_languages(
    conn: sqlite3.Connection, ctx_factory: Any
) -> None:
    char = make_character(conn)
    characters.set_details(
        conn,
        char.id,
        SYSTEM,
        age="twenties",
        appearance="Quick hands",
        languages=("registry-standard", "wolof"),
    )
    ctx = ctx_factory(char)
    me = dispatch(ctx, "look", {"entity": "me"})[0]["character"]
    assert me["languages"] == ["Registry Standard", "Wolof"]
    here = dispatch(ctx, "look", {"entity": "here"})[0]["location"]
    assert here["languages_heard_here"]["Cantonese"] == "most"  # Tarp Row's pocket
    assert here["languages_heard_here"]["Registry Standard"] == "everyone"
    assert here["npcs"][0]["age"] == "forties"


def test_art_shows_once_per_place_and_face(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="hundred-hooks")
    play = PlaySession(
        conn, content, StubClient(say("a"), say("b"), say("c")), DESIGN_TEXT, SeqRng(), char.id
    )
    first = play.start()[2]
    assert [block.splitlines()[-1] for block in first.art] == [
        "  -- The Hundred Hooks --",
        "  -- Nana Priya Seshadri --",
    ]
    play.go("tarp-row")
    back = play.go("hundred-hooks")
    assert back.art == ()
