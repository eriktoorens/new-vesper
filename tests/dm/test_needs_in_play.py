"""Bodily needs in play (D83-D89): counted while online, felt in rolls, eased by commands.

The clock starts at noon on a Tuesday in the Gales, which has no cold or hot feel of
its own; tests that care set the weather.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

import pytest

from new_vesper.budget.policy import stamp
from new_vesper.content.loader import Content
from new_vesper.dm.handlers import dispatch
from new_vesper.dm.needs import exposure_at
from new_vesper.dm.prompt import DM_INSTRUCTIONS
from new_vesper.dm.session import PlaySession, SessionError
from new_vesper.dm.tools import TOOL_NAMES
from new_vesper.rules.clock import weather_block_start
from new_vesper.rules.needs import HOUR, STEP_SECONDS, Exposure, Need, NeedState
from new_vesper.state import characters
from new_vesper.state import needs as stored
from new_vesper.state.events import SYSTEM
from tests.dm.conftest import DESIGN_TEXT, NOON_TUESDAY, SeqRng, StubClient, make_character


class Clock:
    def __init__(self) -> None:
        self.now = NOON_TUESDAY

    def __call__(self) -> datetime:
        return self.now

    def pass_hours(self, hours: float) -> None:
        self.now += timedelta(hours=hours)


def playing(
    conn: sqlite3.Connection, content: Content, location: str = "hundred-hooks", **kw: Any
) -> tuple[PlaySession, Clock]:
    char = make_character(conn, location=location, online=False, **kw)
    clock = Clock()
    play = PlaySession(conn, content, StubClient(), DESIGN_TEXT, SeqRng(4, 4), char.id, now=clock)
    play.start()
    return play, clock


def level(play: PlaySession, need: Need) -> int:
    found = stored.get_needs(play.conn, play.character_id, [need])
    return found[need][0].level


def set_need(play: PlaySession, need: Need, state: NeedState, clock: Clock) -> None:
    stored.save_needs(play.conn, play.character_id, {need: state}, clock.now)


def dm_state(play: PlaySession) -> dict[str, Any]:
    message = play.client.messages.turn_calls[-1]["messages"][0]["content"]
    return json.loads(message.split("<scene_state>")[1].split("</scene_state>")[0])


def test_which_way_a_need_counts_is_stored(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    set_need(play, Need.COLD, NeedState(2, 600, easing=True), clock)
    found = stored.get_needs(conn, play.character_id, [Need.COLD])
    assert found[Need.COLD][0] == NeedState(2, 600, easing=True)


def test_needs_climb_while_playing(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    clock.pass_hours(STEP_SECONDS[Need.HUNGER] / HOUR)
    outcome = play.turn("Mira keeps reading")
    assert level(play, Need.HUNGER) == 1 and level(play, Need.THIRST) == 1
    assert "hunger: peckish" in outcome.changes
    assert "peckish" in outcome.status
    needs = dm_state(play)["character"]["needs"]
    assert needs["hunger"] == {
        "level": 1,
        "of": 3,
        "feels": "peckish",
        "penalty": {},
        "worst": False,
    }


def test_needs_take_off_roll_stats(
    conn: sqlite3.Connection, content: Content, ctx_factory: Any
) -> None:
    char = make_character(conn)  # Steel +1
    ctx = ctx_factory(char, 6, 6)
    stored.save_needs(conn, char.id, {Need.HUNGER: NeedState(2), Need.COLD: NeedState(3)}, ctx.now)
    result, error = dispatch(
        ctx, "call_for_roll", {"stat": "steel", "difficulty": "risky", "stakes": "shove"}
    )
    assert not error
    assert result["stat_value"] == 1 - 1 - 2
    look, _ = dispatch(ctx, "look", {"entity": "me"})
    assert look["character"]["roll_stats"]["steel"] == -2
    assert look["character"]["needs"]["cold"]["penalty"] == {"steel": -2, "slick": -2}


def test_the_worst_level_costs_harm(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    step = STEP_SECONDS[Need.THIRST]
    set_need(play, Need.THIRST, NeedState(2, step - 60), clock)
    clock.pass_hours(1 / 60)
    outcome = play.turn("Mira waits")
    assert play.character.sheet.harm == 1
    assert "harm 0 -> 1" in outcome.changes and "thirst: dehydrated" in outcome.changes
    clock.pass_hours(step / HOUR)
    play.turn("Mira waits")
    assert play.character.sheet.harm == 2


def test_tiredness_at_its_worst_costs_fade(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    set_need(play, Need.TIRED, NeedState(3, 0), clock)
    clock.pass_hours(STEP_SECONDS[Need.TIRED] / HOUR)
    play.turn("Mira keeps her eyes open")
    assert play.character.sheet.fade == 1


def test_needs_can_bring_a_character_to_fall_or_endure(
    conn: sqlite3.Connection, content: Content
) -> None:
    play, clock = playing(conn, content)
    me = play.character
    characters.update_sheet(
        conn, me.id, me.sheet, me.sheet.__class__(**{**me.sheet.__dict__, "harm": 5}), SYSTEM, "x"
    )
    set_need(play, Need.HUNGER, NeedState(3, 0), clock)
    clock.pass_hours(STEP_SECONDS[Need.HUNGER] / HOUR)
    outcome = play.turn("Mira staggers on")
    assert outcome.fall_or_endure_pending
    assert play.character.sheet.harm == 6 and not play.character.sheet.fallen


def test_offline_time_never_counts(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row")
    play.end()
    clock.pass_hours(30)
    play.start()
    play.turn("Mira looks around")
    assert level(play, Need.HUNGER) == 0 and play.character.sheet.harm == 0


def test_logging_off_at_a_haven_clears_needs(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    clock.pass_hours(9)
    play.turn("Mira sits")
    assert level(play, Need.HUNGER) == 2
    play.end()
    assert all(level(play, need) == 0 for need in Need)


def test_logging_off_elsewhere_keeps_them(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row")
    clock.pass_hours(9)
    play.turn("Mira sits")
    play.end()
    assert level(play, Need.HUNGER) == 2


def force_weather(conn: sqlite3.Connection, when: datetime, weather: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO weather (region_id, block_start, weather_id) VALUES (?, ?, ?)",
        ("market", stamp(weather_block_start(when)), weather),
    )


def test_exposure_depends_on_the_place_and_weather(
    conn: sqlite3.Connection, content: Content
) -> None:
    force_weather(conn, NOON_TUESDAY, "sleet")
    assert exposure_at(conn, content, "tarp-row", NOON_TUESDAY) is Exposure.COLD
    assert exposure_at(conn, content, "hundred-hooks", NOON_TUESDAY) is Exposure.NONE
    force_weather(conn, NOON_TUESDAY, "drizzle")
    assert exposure_at(conn, content, "tarp-row", NOON_TUESDAY) is Exposure.NONE
    assert exposure_at(conn, content, "drowned-station", NOON_TUESDAY) is Exposure.COLD
    force_weather(conn, NOON_TUESDAY, "muggy-heat")
    assert exposure_at(conn, content, "the-mudflats", NOON_TUESDAY) is Exposure.HOT


def test_the_cold_bites_out_in_sleet(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row")
    force_weather(conn, clock.now + timedelta(hours=2), "sleet")
    clock.pass_hours(2)
    play.turn("Mira stands in the sleet")
    assert level(play, Need.COLD) == 2
    assert level(play, Need.HEAT) == 0


# --- /eat, /drink, /rest --------------------------------------------------------------


def test_eating_costs_and_clears_hunger(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row")
    set_need(play, Need.HUNGER, NeedState(2, 100), clock)
    before = play.character.currency
    message = play.eat()
    assert "noodles" in message and "5 glitter" in message
    assert play.character.currency == before - 5
    assert level(play, Need.HUNGER) == 0
    assert play.drink().endswith("for 2 glitter.")


def test_free_water_at_the_shrine(conn: sqlite3.Connection, content: Content) -> None:
    play, _ = playing(conn, content, location="umbrella-shrine")
    before = play.character.currency
    assert "rainwater" in play.drink()
    assert play.character.currency == before
    with pytest.raises(SessionError, match="nobody here sells"):
        play.eat()


def test_nothing_is_sold_everywhere(conn: sqlite3.Connection, content: Content) -> None:
    play, _ = playing(conn, content, location="the-mudflats")
    for act in (play.eat, play.drink):
        with pytest.raises(SessionError, match="nobody here sells"):
            act()


def test_no_money_no_meal(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row")
    me = play.character
    characters.adjust_currency(conn, me.id, -me.currency, SYSTEM, "robbed")
    set_need(play, Need.HUNGER, NeedState(2), clock)
    with pytest.raises(SessionError, match="costs 5 glitter"):
        play.eat()
    assert level(play, Need.HUNGER) == 2


def test_resting_only_at_a_haven(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content)
    set_need(play, Need.TIRED, NeedState(3), clock)
    assert "rested" in play.rest()
    assert level(play, Need.TIRED) == 0
    elsewhere, _ = playing(conn, content, location="tarp-row", player_id=2)
    with pytest.raises(SessionError, match="haven"):
        elsewhere.rest()


def test_made_people_neither_eat_nor_drink(conn: sqlite3.Connection, content: Content) -> None:
    play, clock = playing(conn, content, location="tarp-row", origin="made-person")
    clock.pass_hours(20)
    play.turn("Kit waits")
    assert set(dm_state(play)["character"]["needs"]) == {"tired", "heat"}
    with pytest.raises(SessionError, match="doesn't need to eat"):
        play.eat()
    assert level(play, Need.TIRED) == 3


def test_the_dm_cannot_change_needs() -> None:
    assert not any("need" in name for name in TOOL_NAMES)
    assert not TOOL_NAMES & {"eat", "drink", "rest", "feed", "sleep"}
    assert "/eat" in DM_INSTRUCTIONS and "never change them" in DM_INSTRUCTIONS
