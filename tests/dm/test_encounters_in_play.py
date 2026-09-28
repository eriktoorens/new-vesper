"""The DM creates encounters on the fly (D73), spending the district's daily pool."""

import json
import sqlite3
from typing import Any

import pytest

from new_vesper.city.encounters import left_today
from new_vesper.content.loader import Content
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.session import PlaySession
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    say,
    use,
)


def a_kind_left(conn: sqlite3.Connection) -> str:
    return next(
        k
        for k, n in left_today(conn, "market", NOON_TUESDAY).items()
        if n and k != "underside trouble"
    )


def encounter(kind: str, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "what_happens": "A gust tears a tarp loose over the carts.", **extra}


def test_the_dm_creates_one_per_turn(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)
    ctx = ctx_factory(char)
    kind = a_kind_left(conn)
    result, error = dispatch(ctx, "create_encounter", encounter(kind, stranger_role="a porter"))
    assert not error
    assert result["stranger"]["role"] == "a porter"
    assert result["stranger"]["speaks"][-1] == "Registry Standard"
    result, error = dispatch(ctx, "create_encounter", encounter(a_kind_left(conn)))
    assert error and "one encounter per turn" in result["error"]


@pytest.mark.parametrize(
    "args",
    [
        {"kind": "boss-fight", "what_happens": "x"},
        {"kind": "color"},
        {"kind": "color", "what_happens": ""},
        {"kind": "color", "what_happens": "x" * 301},
        {"kind": "color", "what_happens": "x", "stranger_role": ""},
        {"kind": "color", "what_happens": "x", "loot": "a sword"},
        {"kind": "color", "what_happens": "x", "stranger_role": "r" * 121},
    ],
)
def test_bad_encounters_refused(
    conn: sqlite3.Connection, ctx_factory: Any, args: dict[str, Any]
) -> None:
    char = make_character(conn)
    before = left_today(conn, "market", NOON_TUESDAY)
    result, error = dispatch(ctx_factory(char), "create_encounter", args)
    assert error, result
    assert left_today(conn, "market", NOON_TUESDAY) == before


def test_the_dm_sees_the_pool_ideas_and_recent(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="tarp-row")
    kind = a_kind_left(conn)
    client = StubClient(
        say("Steam."), use(("create_encounter", encounter(kind))), say("The tarp snaps free.")
    )
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    play.turn("I wait out the rain under Tomás's awning")
    first = client.messages.turn_calls[0]["messages"][0]["content"]
    state = json.loads(first.split("<scene_state>")[1].split("</scene_state>")[0])
    assert set(state["encounters"]) == {
        "left_today_in_district",
        "ideas_that_fit_here",
        "recently_in_district",
    }
    assert state["encounters"]["recently_in_district"] == []
    play.turn("I help tie it back down")
    later = client.messages.turn_calls[-1]["messages"][0]["content"]
    state = json.loads(later.split("<scene_state>")[1].split("</scene_state>")[0])
    assert state["encounters"]["recently_in_district"][0]["what_happened"].startswith("A gust")
