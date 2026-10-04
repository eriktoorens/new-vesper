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
from new_vesper.city.sky import tide_at
from new_vesper.content.loader import Content
from new_vesper.dm.session import PlaySession
from new_vesper.state.events import list_events
from tests.dm.conftest import DESIGN_TEXT, SeqRng, StubClient, make_character, say

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


def the_pass_says(client: StubClient, reply: str) -> None:
    """Script the cheap after-turn pass (D123, D132); other cheap calls say nothing."""
    client.messages.summary = lambda kwargs: (
        reply if "<turn>" in kwargs["messages"][0]["content"] else "nothing"
    )


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


def test_an_exit_in_the_narration_moves_the_npc(conn: sqlite3.Connection, content: Content) -> None:
    parting = '<say who="nana-priya" lang="registry-standard">Paru is waiting, child.</say>'
    play, clock, client = at_the_hooks(conn, content, say(f"Nana rises and goes. {parting}"))
    the_pass_says(client, "nana-priya | goes to | umbrella-shrine | her offering for Paru")
    clock.pass_minutes(10)
    outcome = play.turn("Mira asks Nana about the bunks")
    assert "Paru is waiting, child." in outcome.narration
    assert "Nana Priya Seshadri leaves" in outcome.changes
    assert not any("Shrine" in change for change in outcome.changes)  # not the character's to see
    assert where(conn, content, "nana-priya", clock.now) == "umbrella-shrine"
    assert not any(line.startswith("Nana Priya") for line in play.who())
    [event] = list_events(conn, kind="npc_went")
    assert event.payload["reason"] == "her offering for Paru"


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
    "line",
    [
        "tomas-haddad | goes to | umbrella-shrine | not here to go",
        "nana-priya | goes to | nowhere-at-all | not a place",
        "nana-priya | goes to | hundred-hooks | already here",
        "nana-priya | goes to | away | her day keeps her in the district",
        "nana-priya | goes to | umbrella-shrine |",
        "nana-priya | went | umbrella-shrine | not the form",
        "Mira | goes to | umbrella-shrine | the player character never",
        "nana-priya | goes to | umbrella-shrine; tomas-haddad | x",
        "nana-priya | goes to | umbrella-shrine | why",  # the template, copied
        "nana-priya | goes to | umbrella-shrine | their reason, in a few words",
    ],
)
def test_moves_code_will_not_make(conn: sqlite3.Connection, content: Content, line: str) -> None:
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."))
    the_pass_says(client, line)
    clock.pass_minutes(10)
    outcome = play.turn("Mira asks Nana about the bunks")
    assert where(conn, content, "nana-priya", clock.now) == "hundred-hooks"
    assert list_events(conn, kind="npc_went") == []
    assert not any("leaves" in change for change in outcome.changes)


def test_no_one_walks_into_a_flooded_place(conn: sqlite3.Connection, content: Content) -> None:
    flats = content.locations["the-mudflats"].tide
    moment = BEFORE_FIVE
    while not (tide_at(flats, moment) and tide_at(flats, moment).closed):
        moment += timedelta(minutes=10)
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."))
    clock.now = moment
    the_pass_says(client, "nana-priya | goes to | the-mudflats | to look at the water")
    play.turn("Mira asks Nana about the tide")
    assert list_events(conn, kind="npc_went") == []


# --- time that passes shows (D114) -------------------------------------------------


def test_a_long_gap_reaches_the_narrator(conn: sqlite3.Connection, content: Content) -> None:
    # Fourth playtest: three hours in the cold, then a whole night, and the scene carried on
    # as if no time had passed.
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."), say("Later."))
    play.turn("Mira sits by the kettle")
    assert "time_passed" not in scene_state(client)
    clock.pass_minutes(3 * 60 + 9)
    play.turn("Mira looks up")
    assert scene_state(client)["time_passed"] == {
        "since_last_turn": "3 hours 9 minutes",
        "last_turn_was": "Tuesday 4:55 pm, afternoon",
    }


def test_a_short_gap_is_not_news(conn: sqlite3.Connection, content: Content) -> None:
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."), say("Hm."))
    play.turn("Mira sits by the kettle")
    clock.pass_minutes(14)
    play.turn("Mira looks up")
    assert "time_passed" not in scene_state(client)


def test_a_new_scene_starts_without_a_gap(conn: sqlite3.Connection, content: Content) -> None:
    play, clock, client = at_the_hooks(conn, content, say("Nana looks up."), say("The Row."))
    play.turn("Mira sits by the kettle")
    clock.pass_minutes(60)
    play.go("tarp-row")
    assert "time_passed" not in scene_state(client)


# --- arriving together (from the fifth playtest's third session) ---------------------


def who_is_here(client: StubClient) -> dict[str, Any]:
    message = client.messages.turn_calls[-1]["messages"][0]["content"]
    return json.loads(message.split("<who_is_here>")[1].split("</who_is_here>")[0])


def test_an_npc_who_walked_here_with_you_knows_you_are_here(
    conn: sqlite3.Connection, content: Content
) -> None:
    # Tomás left for the Weighhouse with Brightfin, then startled when Brightfin arrived.
    parting = "Nana rises. Brightfin falls in beside her, out into the drizzle."
    play, clock, client = at_the_hooks(
        conn, content, say(parting), say("The shrine."), say("She lights a stick.")
    )
    the_pass_says(client, "nana-priya | goes to | umbrella-shrine | her offering for Paru")
    clock.pass_minutes(10)
    play.turn("Mira walks with Nana")
    play.go("umbrella-shrine")
    assert scene_state(client)["just_before"] == {
        "where": "The Hundred Hooks",
        "last_narration": parting,
        "came_with_you": ["Nana Priya Seshadri"],
    }
    [nana] = [o for o in who_is_here(client)["others_here"] if o["name"].startswith("Nana")]
    assert nana["came_with_you"] is True
    play.turn("Mira waits while Nana lights the incense")
    assert "just_before" not in scene_state(client)  # the arrival only
    [nana] = [o for o in who_is_here(client)["others_here"] if o["name"].startswith("Nana")]
    assert nana["came_with_you"] is True  # still true all scene


def test_an_npc_who_went_elsewhere_did_not_come_with_you(
    conn: sqlite3.Connection, content: Content
) -> None:
    play, clock, client = at_the_hooks(conn, content, say("Nana goes."), say("Tarp Row."))
    the_pass_says(client, "nana-priya | goes to | umbrella-shrine | her offering for Paru")
    clock.pass_minutes(10)
    play.turn("Mira watches Nana go")
    play.go("tarp-row")
    assert scene_state(client)["just_before"]["came_with_you"] == []
    assert not any("came_with_you" in o for o in who_is_here(client)["others_here"])


def test_a_new_session_starts_with_nothing_just_before(
    conn: sqlite3.Connection, content: Content
) -> None:
    _, _, client = at_the_hooks(conn, content)
    assert "just_before" not in scene_state(client)
