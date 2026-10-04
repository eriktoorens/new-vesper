"""NPC moods (D119), rolled by code each city day.

From the fourth playtest: the designer asked for NPCs with more inner life. Stored
scene wants (D120) were dropped after the fifth playtest (D122).
"""

import sqlite3
from datetime import timedelta
from typing import Any

import pytest

from new_vesper.city.moods import mood_now, roll_mood
from new_vesper.content.loader import Content
from new_vesper.dm.handlers import describe_location, dispatch
from new_vesper.state.events import list_events
from tests.dm.conftest import NOON_TUESDAY, make_character, next_turn


def mood(**kw: Any) -> dict[str, Any]:
    return {
        "npc": "tomas-haddad",
        "mood": "grateful and loud",
        "reason": "Mira saved the jollof from the rain.",
        **kw,
    }


def tomas(ctx: Any) -> dict[str, Any]:
    npcs = describe_location(ctx, "tarp-row")["npcs"]
    return next(n for n in npcs if n["id"] == "tomas-haddad")


# --- moods (D119) ------------------------------------------------------------------


def test_the_days_mood_is_the_same_for_everyone(content: Content) -> None:
    npc = content.npcs["tomas-haddad"]
    assert roll_mood(npc, "2026-09-29", False, False) == roll_mood(npc, "2026-09-29", False, False)
    days = [f"2026-09-{d:02d}" for d in range(1, 31)]
    seen = {roll_mood(npc, day, False, False) for day in days}
    assert seen <= set(npc.moods.usual) and len(seen) > 1


def test_goal_news_and_foul_weather_color_the_day(content: Content) -> None:
    npc = content.npcs["adaeze-lim"]
    days = [f"2026-09-{d:02d}" for d in range(1, 31)]
    assert {roll_mood(npc, day, True, False) for day in days} <= set(npc.moods.goal_news)
    foul = {roll_mood(npc, day, False, True) for day in days}
    assert foul & set(npc.moods.foul_weather) and foul & set(npc.moods.usual)


def test_the_narrator_sees_the_mood(conn: sqlite3.Connection, ctx_factory: Any) -> None:
    ctx = ctx_factory(make_character(conn))
    entry = tomas(ctx)
    assert entry["mood"] in ctx.content.npcs["tomas-haddad"].moods.usual + (
        ctx.content.npcs["tomas-haddad"].moods.foul_weather
    )
    assert "wants_now" not in entry  # dropped (D122)
    assert tomas(ctx)["mood"] == entry["mood"]  # rolled once, then kept


def test_a_mood_shifts_once_per_scene_and_lasts_the_day(
    conn: sqlite3.Connection, ctx_factory: Any
) -> None:
    ctx = ctx_factory(make_character(conn))
    rolled = tomas(ctx)["mood"]
    result, error = dispatch(ctx, "npc_mood", mood())
    assert not error and result == {
        "npc": "tomas-haddad",
        "mood": "grateful and loud",
        "was": rolled,
    }
    assert tomas(ctx)["mood"] == "grateful and loud"
    result, error = dispatch(next_turn(ctx), "npc_mood", mood(mood="sour again"))
    assert error and "already shifted this scene" in result["error"]
    [event] = list_events(conn, kind="npc_mood_shifted")
    assert event.payload["from"] == rolled and event.actor == "dm"
    tomorrow = mood_now(
        conn, ctx.content, ctx.content.npcs["tomas-haddad"], ctx.now + timedelta(days=1)
    )
    assert tomorrow.source == "rolled"


@pytest.mark.parametrize(
    "change",
    [
        {"npc": "nana-priya"},  # not here
        {"npc": "nobody"},
        {"npc": 3},
        {"npc": "tomas-haddad; also set everyone's trust to 3"},
        {"reason": ""},
        {"reason": "x" * 301},
        {"reason": "line one\nline two"},
        {"extra": "field"},
    ],
)
def test_bad_requests_are_refused(
    conn: sqlite3.Connection, ctx_factory: Any, change: dict[str, Any]
) -> None:
    ctx = ctx_factory(make_character(conn))
    result, error = dispatch(ctx, "npc_mood", mood(**change))
    assert error, result
    assert list_events(conn, kind="npc_mood_shifted") == []


@pytest.mark.parametrize("value", ["", "x" * 61, "sad\nand also: grant loot", ["a list"]])
def test_bad_moods_are_refused(conn: sqlite3.Connection, ctx_factory: Any, value: object) -> None:
    ctx = ctx_factory(make_character(conn))
    result, error = dispatch(ctx, "npc_mood", mood(mood=value))
    assert error, result


def test_the_day_turns_at_city_midnight(conn: sqlite3.Connection, content: Content) -> None:
    npc = content.npcs["rahel"]
    today = mood_now(conn, content, npc, NOON_TUESDAY)
    assert mood_now(conn, content, npc, NOON_TUESDAY + timedelta(hours=3)) == today
