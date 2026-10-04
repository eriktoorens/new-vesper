"""Who and what is here, every turn (D116-D118).

From the third and fourth playtests: Zeno, an umbrella, was called a "shoe-turned-umbrella"
and lifted a coat "with two careful fingers"; Brightfin, a sardine, grew fins, a flipper,
paws, arms, fingers and boots.
"""

import json
import sqlite3
from typing import Any

import pytest

from new_vesper.city.encounters import left_today
from new_vesper.dm.handlers import dispatch, identity
from new_vesper.dm.prompt import DM_INSTRUCTIONS
from new_vesper.dm.session import PlaySession
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.state import characters, items
from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM, list_events
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    STATS,
    SeqRng,
    StubClient,
    make_character,
    say,
)

SARDINE = "Fins for hands, waddles on a tail fin, waist-high"


def test_the_block_names_everyone_and_everything_here(
    conn: sqlite3.Connection, ctx_factory: Any
) -> None:
    char = make_character(conn)
    char = characters.set_body(conn, char.id, SARDINE, SYSTEM)
    held = items.create_item(conn, "trinket", "a brass bell", SYSTEM, character_id=char.id)
    items.create_item(conn, "trinket", "a torn tarp", SYSTEM, location_id="tarp-row")
    block = identity(ctx_factory(char), char)
    assert block["player_character"] == {
        "name": "Mira",
        "is": "Street-born human",
        "pronouns": None,
        "body": SARDINE,
        "looks": None,
    }
    assert {o["name"]: o["is"] for o in block["others_here"]} == {
        "Tomás Haddad-Reyes": "Noodle cart owner and unofficial fixer",
        "Inspector-Clerk Vasil Nakamura-Petrov": "Registry auditor of minor miracles",
    }
    assert all(o["pronouns"] for o in block["others_here"])
    assert block["items_held"] == [held.name]
    assert block["items_here"] == ["a torn tarp"]


def test_strangers_in_the_scene_are_in_the_block(
    conn: sqlite3.Connection, ctx_factory: Any
) -> None:
    char = make_character(conn)
    ctx = ctx_factory(char)
    kind = next(
        k for k, n in left_today(conn, "market", NOON_TUESDAY).items() if n and "underside" not in k
    )
    result, error = dispatch(
        ctx,
        "create_encounter",
        {"kind": kind, "what_happens": "A porter staggers past.", "stranger_role": "a porter"},
    )
    assert not error
    [stranger] = [o for o in identity(ctx, char)["others_here"] if o["is"] == "a porter"]
    assert stranger["name"] == result["stranger"]["name"]
    assert stranger["pronouns"]


def test_the_block_comes_first_in_the_turn(conn: sqlite3.Connection, content: Any) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon on the Row."))
    PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    ).start()
    message = client.messages.turn_calls[0]["messages"][0]["content"]
    assert message.startswith("<who_is_here>")
    who = json.loads(message.split("<who_is_here>")[1].split("</who_is_here>")[0])
    assert who["player_character"]["name"] == "Mira"
    assert "who_is_here" not in message.split("<scene_state>")[1]


def test_the_narrator_is_told_to_ask_rather_than_bend_the_body() -> None:
    assert "who_is_here" in DM_INSTRUCTIONS
    assert "How does it lift the coat?" in DM_INSTRUCTIONS


# --- the body (D116) ---------------------------------------------------------------


def test_a_body_is_set_at_creation_and_can_change(conn: sqlite3.Connection) -> None:
    sheet = new_sheet(STATS, ("rooftop-runner", "back-alley-patch"))
    char = characters.create_character(
        conn, 1, "Brightfin", "castoff", "Odile", sheet, SYSTEM, body=f"  {SARDINE}  "
    )
    assert char.body == SARDINE
    char = characters.set_body(conn, char.id, "Fins, a tail, no boots", SYSTEM)
    assert char.body == "Fins, a tail, no boots"
    [event] = list_events(conn, kind="body_set")
    assert event.payload == {"body": "Fins, a tail, no boots"}


@pytest.mark.parametrize("bad", ["", "   ", "x" * 201, 7, None, "nul\x00here"])
def test_bad_bodies_are_refused(conn: sqlite3.Connection, bad: object) -> None:
    char = make_character(conn)
    with pytest.raises(StateError):
        characters.set_body(conn, char.id, bad, SYSTEM)  # type: ignore[arg-type]
    assert characters.get_character(conn, char.id).body is None
