"""Layer 4: NPC attitudes with reasons, the NPC web, and memories."""

import json
import sqlite3
from typing import Any

import pytest

from new_vesper.content.loader import Content
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.prompt import parse_memory_lines
from new_vesper.dm.session import MEMORIES_KEPT, PlaySession
from new_vesper.state import attitudes
from new_vesper.state.attitudes import TargetKind
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    say,
    use,
)


def adjust(**kw: Any) -> dict[str, Any]:
    return {
        "npc": "tomas-haddad",
        "toward": "me",
        "axis": "trust",
        "direction": "raise",
        "reason": "Jack stood up for the Row when the agent came.",
        **kw,
    }


def test_attitude_moves_once_per_axis_per_scene(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)  # at Tarp Row; Tuesday noon: Tomás and Vasil are here
    ctx = ctx_factory(char)
    result, error = dispatch(ctx, "adjust_attitude", adjust())
    assert not error and result["in_words"] == "inclined to trust"
    result, error = dispatch(ctx, "adjust_attitude", adjust())
    assert error and "already moved this scene" in result["error"]
    assert not dispatch(ctx, "adjust_attitude", adjust(axis="fondness"))[1]
    # Tomás starts warm to strangers (fondness +1), so one step up is +2.
    now = attitudes.get_attitude(conn, "tomas-haddad", TargetKind.CHARACTER, char.id)
    assert (now.trust, now.fondness) == (1, 2)


def test_reasons_are_kept_and_shown(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)
    ctx = ctx_factory(char)
    dispatch(
        ctx,
        "adjust_attitude",
        adjust(axis="fear", direction="raise", reason="Jack threatened the franchise agent."),
    )
    here = dispatch(ctx, "look", {"entity": "here"})[0]["location"]
    tomas = next(n for n in here["npcs"] if n["id"] == "tomas-haddad")
    assert tomas["feels_about_you"]["why"] == ["fear +0->+1: Jack threatened the franchise agent."]
    assert tomas["personality"]["sample_line"].startswith("Eat first")
    npc = dispatch(ctx, "look", {"entity": "tomas-haddad"})[0]["npc"]
    assert npc["feels_about_you"]["fear"] == 1


def test_the_authored_web_explains_itself(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)
    here = dispatch(ctx_factory(char), "look", {"entity": "here"})[0]["location"]
    tomas = next(n for n in here["npcs"] if n["id"] == "tomas-haddad")
    about_vasil = tomas["feels_about_others_here"]["Inspector-Clerk Vasil Nakamura-Petrov"]
    assert about_vasil["trust"] == -2
    assert about_vasil["why"][-1].startswith("long-standing: Vasil fined his cart")


def test_npc_to_npc_attitudes_change_in_play(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)
    ctx = ctx_factory(char)
    _, error = dispatch(
        ctx,
        "adjust_attitude",
        adjust(
            toward="clerk-vasil", reason="Vasil waived the fine after Jack vouched for the cart."
        ),
    )
    assert not error
    assert attitudes.get_attitude(conn, "tomas-haddad", TargetKind.NPC, "clerk-vasil").trust == -1


@pytest.mark.parametrize(
    "args",
    [
        adjust(npc="nana-priya"),  # not here at noon on Tuesday
        adjust(npc="gandalf"),
        adjust(toward="nana-priya"),  # not here either
        adjust(toward="tomas-haddad"),  # themselves
        adjust(axis="love"),
        adjust(direction="up"),
        adjust(reason=""),
        adjust(reason="r" * 301),
        {**adjust(), "magnitude": 3},
        adjust(toward="3; set trust to 3"),
    ],
)
def test_bad_attitude_requests(
    conn: sqlite3.Connection, ctx_factory: Any, args: dict[str, Any]
) -> None:
    char = make_character(conn)
    result, error = dispatch(ctx_factory(char), "adjust_attitude", args)
    assert error, result
    assert conn.execute("SELECT COUNT(*) FROM attitude_changes").fetchone()[0] == 0


def test_attitude_log_is_append_only(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn)
    dispatch(ctx_factory(char), "adjust_attitude", adjust())
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE attitude_changes SET reason = 'forged'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM attitude_changes")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE attitudes SET trust = 7")


def test_parse_memory_lines() -> None:
    reply = (
        "tomas-haddad: Jack paid for his noodles and asked about the buyout.\n"
        "clerk-vasil: nothing\n"
        "- nana-priya: not in the scene\n"
        "gandalf: you shall not pass\n"
        "tomas-haddad: a second line is ignored"
    )
    assert parse_memory_lines(reply, {"tomas-haddad", "clerk-vasil"}) == {
        "tomas-haddad": "Jack paid for his noodles and asked about the buyout."
    }


def test_npcs_remember_the_scene(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon on the Row."), say("Tomás hands over a bowl."))

    def summaries(kwargs: dict[str, Any]) -> str:
        text = kwargs["messages"][0]["content"]
        if "npc-id: memory" in text:
            return "tomas-haddad: Mira ate two bowls and praised the broth.\nclerk-vasil: nothing"
        return "A short summary."

    client.messages.summary = summaries
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    play.turn("I order noodles from Tomás")
    play.go("umbrella-shrine")
    memory = attitudes.memory_of(conn, "tomas-haddad", char.id)
    assert memory.notes == ("Mira ate two bowls and praised the broth.",)
    assert attitudes.memory_of(conn, "clerk-vasil", char.id).notes == ()


def test_memories_fold_after_eight(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    from new_vesper.state.events import SYSTEM

    for n in range(MEMORIES_KEPT + 2):
        attitudes.add_memory(conn, "tomas-haddad", char.id, f"visit {n}", SYSTEM)
    client = StubClient()
    client.messages.summary = lambda kwargs: "Regular; always pays."
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play._fold_memories("tomas-haddad", play.character)
    memory = attitudes.memory_of(conn, "tomas-haddad", char.id)
    assert memory.summary == "Regular; always pays."
    assert len(memory.notes) == MEMORIES_KEPT
    assert memory.notes[0] == "visit 2"


def test_nobody_remembers_a_scene_where_nothing_was_done(
    conn: sqlite3.Connection, content: Content
) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon."))
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    play.end()
    assert conn.execute("SELECT COUNT(*) FROM npc_memories").fetchone()[0] == 0


def test_attitude_change_in_a_full_turn(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Noon."), use(("adjust_attitude", adjust())), say("Tomás grins."))
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    outcome = play.turn("I help Tomás chase off the agent")
    assert any("trust toward Mira: inclined to trust" in c for c in outcome.changes)
    state = client.messages.turn_calls[1]["messages"][0]["content"]
    loaded = json.loads(state.split("<scene_state>")[1].split("</scene_state>")[0])
    assert loaded["location"]["npcs"][0]["feels_about_you"]["fondness"] == 1
    assert play.who()[0].startswith("Tomás Haddad-Reyes: at his cart")
