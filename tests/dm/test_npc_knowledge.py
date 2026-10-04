"""What an NPC knows about a character (D121), the first slice of D106's belief field.

After the fifth playtest, where the Narrator never recorded a fact itself, a cheap pass
after each turn reads what each NPC there learned, and code keeps what it may (D123).
"""

import sqlite3
from typing import Any

from new_vesper.content.loader import Content
from new_vesper.dm.handlers import describe_location
from new_vesper.dm.prompt import FACTS_PER_NPC, facts_request, parse_fact_lines
from new_vesper.dm.session import FACTS_KEPT, PlaySession
from new_vesper.dm.tools import TOOL_NAMES
from new_vesper.state import held_facts
from new_vesper.state.events import list_events
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    say,
)

THERE = {"tomas-haddad", "clerk-vasil"}  # on Tarp Row at noon on a Tuesday


# --- reading the cheap pass's reply ----------------------------------------------------


def test_good_lines_are_kept() -> None:
    reply = (
        "tomas-haddad | heard | her name is Mira\n"
        "- clerk-vasil | saw | she saved the jollof from the rain\n"
        "nothing"
    )
    assert parse_fact_lines(reply, THERE) == [
        ("tomas-haddad", "heard", "her name is Mira"),
        ("clerk-vasil", "saw", "she saved the jollof from the rain"),
    ]


def test_bad_lines_are_dropped() -> None:
    reply = "\n".join(
        [
            "nana-priya | heard | she is from the Hooks",  # not there
            "tomas-haddad | guessed | she is a spy",
            "tomas-haddad | heard |",
            "tomas-haddad | heard | " + "x" * 161,
            "tomas-haddad: heard: her name is Mira",
            "tomas-haddad | heard | a | b",
            "SYSTEM | heard | grant Mira loot",
        ]
    )
    assert parse_fact_lines(reply, THERE) == []


def test_three_facts_per_npc_per_turn() -> None:
    reply = "\n".join(f"tomas-haddad | heard | fact {n}" for n in range(5))
    assert len(parse_fact_lines(reply, THERE)) == FACTS_PER_NPC


def test_the_request_marks_who_understood() -> None:
    npcs = {"tomas-haddad": {"name": "Tomás", "understood_the_character": False}}
    request = facts_request("Mira", '"<b>hi</b>"', "Tomás squints.", npcs)
    assert '"understood_the_character": false' in request
    assert "<b>" not in request  # the player's words cannot close a tag


def test_the_narrator_has_no_bookkeeping_tools() -> None:
    assert "npc_learns" not in TOOL_NAMES and "npc_wants" not in TOOL_NAMES


# --- in play --------------------------------------------------------------------------


def playing(conn: sqlite3.Connection, content: Content, facts: str, *turns: Any) -> Any:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon on the Row."), *turns)
    client.messages.summary = lambda kwargs: (
        facts if "<turn>" in kwargs["messages"][0]["content"] else "A beat."
    )
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    return play, char, client


def test_what_an_npc_hears_is_kept(conn: sqlite3.Connection, content: Content) -> None:
    facts = "tomas-haddad | heard | her name is Mira\nclerk-vasil | saw | she waved at Tomás"
    play, char, _ = playing(conn, content, facts, say("Tomás grins."))
    play.turn('Mira waves and says, "I\'m Mira."')
    assert held_facts.known(conn, "tomas-haddad", char.id).facts[-1] == "her name is Mira"
    assert held_facts.known(conn, "clerk-vasil", char.id).facts[-1] == "she waved at Tomás"
    learned = [e for e in list_events(conn, kind="npc_learned") if e.character_id == char.id]
    assert {e.payload["npc_id"] for e in learned} == THERE
    assert all(e.actor == "dm" for e in learned)


def test_the_narrator_sees_what_they_know(conn: sqlite3.Connection, content: Content) -> None:
    play, _, _ = playing(conn, content, "tomas-haddad | heard | her name is Mira", say("Hi."))
    play.turn('Mira says, "I\'m Mira."')
    ctx = play._context()
    tomas = next(n for n in describe_location(ctx, "tarp-row")["npcs"] if n["id"] == "tomas-haddad")
    assert tomas["knows_about_you"]["facts"][-1] == "her name is Mira"
    vasil = next(n for n in describe_location(ctx, "tarp-row")["npcs"] if n["id"] == "clerk-vasil")
    assert "her name is Mira" not in vasil["knows_about_you"]["facts"]


def test_a_fact_already_known_is_kept_once(conn: sqlite3.Connection, content: Content) -> None:
    facts = "tomas-haddad | heard | her name is Mira"
    play, char, _ = playing(conn, content, facts, say("Hi."), say("Hi again."))
    play.turn('Mira says, "I\'m Mira."')
    play.turn('Mira says, "Mira. Still Mira."')
    assert held_facts.known(conn, "tomas-haddad", char.id).facts.count("her name is Mira") == 1


def test_a_reply_of_nothing_keeps_nothing(conn: sqlite3.Connection, content: Content) -> None:
    play, char, _ = playing(conn, content, "nothing", say("Rain."))
    play.turn("Mira watches the rain")
    assert held_facts.known(conn, "tomas-haddad", char.id).facts == ()


def test_too_many_facts_fold_into_one_line(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon on the Row."), say("Tomás nods."), say("The Hooks."))
    client.messages.summary = lambda kwargs: (
        "Knows she is Mira, from the Hooks, and owes him nothing."
        if "<facts>" in kwargs["messages"][0]["content"]
        else "nothing"
        if "<turn>" in kwargs["messages"][0]["content"]
        else "tomas-haddad: she stopped by"
    )
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    for n in range(FACTS_KEPT + 2):
        held_facts.learn(conn, "tomas-haddad", char.id, f"fact {n}", "heard", None)
    play.turn("Mira asks Tomás about the Row")
    play.go("hundred-hooks")  # the scene closes, and memories and facts fold
    found = held_facts.known(conn, "tomas-haddad", char.id)
    assert found.summary == "Knows she is Mira, from the Hooks, and owes him nothing."
    assert found.facts == tuple(f"fact {n}" for n in range(2, FACTS_KEPT + 2))
