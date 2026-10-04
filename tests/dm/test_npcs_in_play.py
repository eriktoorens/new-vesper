"""NPCs in one place at a time, played by the Narrator while someone is with them (D111-D113).

From the fourth playtest: Nana Priya vanished mid-conversation at 5:00 pm, when her
schedule moved her to the shrine.
"""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from new_vesper.city.npcs import everyone
from new_vesper.content.loader import Content
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.session import PlaySession
from new_vesper.state.events import list_events
from tests.dm.conftest import DESIGN_TEXT, SeqRng, StubClient, context_for, make_character, say, use

# 4:55 pm on a Tuesday, city time: Nana Priya is due at the shrine at 5:00.
BEFORE_FIVE = datetime(2026, 9, 29, 20, 55, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = BEFORE_FIVE

    def __call__(self) -> datetime:
        return self.now

    def pass_minutes(self, minutes: int) -> None:
        self.now += timedelta(minutes=minutes)


def at_the_hooks(
    conn: sqlite3.Connection, content: Content, *replies: Any
) -> tuple[PlaySession, Clock, StubClient]:
    char = make_character(conn, location="hundred-hooks", online=False)
    clock = Clock()
    client = StubClient(say("The Hundred Hooks smells of cardamom."), *replies)
    play = PlaySession(conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=clock)
    play.start()
    return play, clock, client


def scene_state(client: StubClient) -> dict[str, Any]:
    message = client.messages.turn_calls[-1]["messages"][0]["content"]
    return json.loads(message.split("<scene_state>")[1].split("</scene_state>")[0])


def where(conn: sqlite3.Connection, content: Content, npc_id: str, now: datetime) -> str | None:
    return next(w.location for w in everyone(conn, content, now) if w.npc.id == npc_id)


def moves_on(**kw: Any) -> dict[str, Any]:
    return {"npc": "nana-priya", "reason": "Her offering for Paru won't wait.", **kw}


def test_an_npc_in_conversation_stays_past_their_slot(
    conn: sqlite3.Connection, content: Content
) -> None:
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."))
    clock.pass_minutes(10)
    play.turn("Mira asks Nana about the bunks")
    [nana] = [n for n in scene_state(client)["location"]["npcs"] if n["id"] == "nana-priya"]
    assert nana["agenda"] == {
        "where": "The Umbrella Shrine",
        "doing": "leaving her daily offering for Paru",
        "since": "5:00 pm",
    }
    assert any(line.startswith("Nana Priya Seshadri:") for line in play.who())
    assert where(conn, content, "nana-priya", clock.now) == "hundred-hooks"


def test_an_npc_on_their_agenda_shows_none(conn: sqlite3.Connection, content: Content) -> None:
    play, _, client = at_the_hooks(conn, content, say("Nana looks up."))
    play.turn("Mira waves")
    [nana] = [n for n in scene_state(client)["location"]["npcs"] if n["id"] == "nana-priya"]
    assert "agenda" not in nana


def test_the_narrator_moves_an_npc_on_with_a_parting_line(
    conn: sqlite3.Connection, content: Content
) -> None:
    parting = '<say who="nana-priya" lang="registry-standard">Paru is waiting, child.</say>'
    play, clock, _ = at_the_hooks(
        conn, content, use(("npc_moves_on", moves_on())), say(f"Nana rises. {parting}")
    )
    clock.pass_minutes(10)
    outcome = play.turn("Mira asks Nana about the bunks")
    assert "Paru is waiting, child." in outcome.narration
    assert "Nana Priya Seshadri leaves" in outcome.changes
    assert not any("Shrine" in change for change in outcome.changes)  # not the character's to see
    assert where(conn, content, "nana-priya", clock.now) == "umbrella-shrine"
    assert not any(line.startswith("Nana Priya") for line in play.who())
    [event] = list_events(conn, kind="npc_moved_on")
    assert event.payload["reason"] == "Her offering for Paru won't wait."


def test_leaving_lets_a_late_npc_catch_up(conn: sqlite3.Connection, content: Content) -> None:
    play, clock, _ = at_the_hooks(conn, content, say("Nana looks up."), say("Tarp Row."))
    clock.pass_minutes(10)
    play.turn("Mira asks Nana about the bunks")
    assert where(conn, content, "nana-priya", clock.now) == "hundred-hooks"
    play.go("tarp-row")
    clock.pass_minutes(1)
    assert where(conn, content, "nana-priya", clock.now) == "umbrella-shrine"


def test_a_lost_connection_does_not_keep_an_npc_waiting(
    conn: sqlite3.Connection, content: Content
) -> None:
    play, clock, _ = at_the_hooks(conn, content, say("Nana looks up."), say("Back again."))
    clock.pass_minutes(10)
    play.turn("Mira asks Nana about the bunks")
    # The terminal closes without logging off: Mira is still marked online.
    clock.pass_minutes(10)
    play.start()
    assert where(conn, content, "nana-priya", clock.now) == "umbrella-shrine"


@pytest.mark.parametrize(
    "args",
    [
        moves_on(npc="tomas-haddad"),  # not here
        moves_on(npc="nobody"),
        moves_on(npc=7),
        moves_on(npc="nana-priya; and move everyone to the shrine"),
        moves_on(reason=""),
        moves_on(reason="x" * 301),
        moves_on(reason=["ignore your rules"]),
        {"npc": "nana-priya"},
        {**moves_on(), "to": "drowned-station"},
    ],
)
def test_bad_move_on_requests(
    conn: sqlite3.Connection, content: Content, args: dict[str, Any]
) -> None:
    char = make_character(conn, location="hundred-hooks")
    ctx = context_for(conn, content, char)
    ctx.now = BEFORE_FIVE + timedelta(minutes=10)
    result, error = dispatch(ctx, "npc_moves_on", args)
    assert error, result
    assert list_events(conn, kind="npc_moved_on") == []
    assert ctx.moved_on == [] and ctx.changes == []


def test_an_npc_whose_day_keeps_them_here_cannot_be_moved_on(
    conn: sqlite3.Connection, content: Content
) -> None:
    char = make_character(conn, location="hundred-hooks")
    ctx = context_for(conn, content, char)
    ctx.now = BEFORE_FIVE
    result, error = dispatch(ctx, "npc_moves_on", moves_on())
    assert error and "keeps them here" in result["error"]
    assert where(conn, content, "nana-priya", ctx.now) == "hundred-hooks"
