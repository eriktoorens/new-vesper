"""Layer 3 in play: the DM sees the time and weather; the recap keeps secrets."""

import json
import sqlite3
from datetime import timedelta
from typing import Any

from new_vesper.content.loader import Content
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.session import PlaySession
from new_vesper.state import characters
from new_vesper.state.events import SYSTEM
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    next_turn,
    say,
)


def test_state_has_time_weather_and_schedules(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False, location="tarp-row")
    client = StubClient(say("Noon on the Row."))
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    outcome = play.start()[2]
    message = client.messages.turn_calls[0]["messages"][0]["content"]
    state = json.loads(message.split("<scene_state>")[1].split("</scene_state>")[0])
    assert state["time"] == "Tuesday 12:00 pm, midday"
    assert state["weather"]["now"]
    npcs = {n["name"]: n["doing"] for n in state["location"]["npcs"]}
    assert set(npcs) == {"Tomás Haddad-Reyes", "Inspector-Clerk Vasil Nakamura-Petrov"}
    assert outcome.status.startswith("Tuesday 12:00 pm, midday; ")


def test_absent_regulars_come_with_where(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    char = make_character(conn, location="weighhouse")
    here = dispatch(ctx_factory(char), "look", {"entity": "here"})[0]["location"]
    assert here["npcs"] == []
    assert here["regulars_elsewhere"][0]["where"] == "Tarp Row"


def test_knack_days_turn_over_at_city_midnight(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    hacker = make_character(conn, knacks=("shrine-question", "read-the-crowd"))
    ctx = ctx_factory(hacker, 4, 4, 4, 4)
    args = {
        "stat": "weird",
        "difficulty": "risky",
        "stakes": "ask Paru",
        "knack": "shrine-question",
    }
    assert not dispatch(ctx, "call_for_roll", args)[1]
    # The roll happened at noon on Tuesday, city time.
    conn.execute("UPDATE rolls SET created_at = '2026-09-29T16:00:00.000Z'")
    result, error = dispatch(next_turn(ctx), "call_for_roll", args)
    assert error and "used up" in result["error"]
    ctx.now = NOON_TUESDAY + timedelta(hours=12, minutes=30)  # 0:30 am Wednesday, city time
    assert not dispatch(next_turn(ctx), "call_for_roll", args)[1]


def test_recap_keeps_npc_secrets(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    characters.set_online(conn, char.id, True, SYSTEM)
    characters.set_online(conn, char.id, False, SYSTEM)
    later = NOON_TUESDAY + timedelta(days=30)
    client = StubClient(say("Back."))
    play = PlaySession(conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: later)
    play.start()
    recap_calls = [
        c
        for c in client.messages.calls
        if "tools" not in c and "returning" in c["messages"][0]["content"]
    ]
    assert recap_calls, "the neglect of the Market should be in a recap"
    sent = recap_calls[0]["messages"][0]["content"]
    assert "npc_goal_advanced" not in sent and "Registry reply" not in sent
    assert "light_changed" in sent


def test_tide_forces_a_harder_rung(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    from datetime import UTC, datetime

    from new_vesper.rules.sky import tide

    char = make_character(conn, location="tidewater-stairs")
    ctx = ctx_factory(char, 4, 4)
    moment = datetime(2026, 10, 3, tzinfo=UTC)
    while not tide(moment).turning:
        moment += timedelta(minutes=10)
    ctx.now = moment
    result, error = dispatch(
        ctx, "call_for_roll", {"stat": "slick", "difficulty": "routine", "stakes": "cross"}
    )
    assert not error
    assert result["difficulty"] == "hard"
    assert any("the tide makes this hard" in note for note in result["notes"])


def test_cannot_walk_onto_flooded_flats(conn: sqlite3.Connection, content: Content) -> None:
    from datetime import UTC, datetime

    import pytest

    from new_vesper.dm.session import SessionError
    from new_vesper.rules.sky import TideState, tide

    moment = datetime(2026, 10, 3, tzinfo=UTC)
    while tide(moment).state is not TideState.HIGH:
        moment += timedelta(minutes=10)
    char = make_character(conn, online=False, location="tidewater-stairs")
    play = PlaySession(
        conn, content, StubClient(say("Gulls.")), DESIGN_TEXT, SeqRng(), char.id, now=lambda: moment
    )
    play.start()
    with pytest.raises(SessionError, match="under water"):
        play.go("the-mudflats")
    assert " tide" in play.status_line()
