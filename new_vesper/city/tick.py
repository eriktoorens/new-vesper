"""The daily city tick (D55): Light neglect and NPC goals, once per city day.

It runs whenever anyone plays, catching up on days nobody was around, so the
city keeps moving without a server.
"""

import sqlite3
from datetime import date, datetime, timedelta

from new_vesper.content.loader import Content
from new_vesper.rules.clock import city_day, city_time
from new_vesper.rules.light import apply_neglect
from new_vesper.state import world
from new_vesper.state.db import atomic
from new_vesper.state.events import SYSTEM, append_event, list_events

# Neglected regions lose 1 Light per in-game week (design doc, Shared Play).
NEGLECT_DAYS = 7
# Days nobody played beyond this are not replayed one by one.
MAX_CATCH_UP_DAYS = 14


def _event_day(event_created_at: str, payload: dict[str, object]) -> date:
    stamped = payload.get("city_day")
    if isinstance(stamped, str):
        return date.fromisoformat(stamped)
    return city_time(datetime.fromisoformat(event_created_at.replace("Z", "+00:00"))).date()


def _last_cared_for(conn: sqlite3.Connection, region_id: str) -> date | None:
    """The last day this region's Light was raised or neglect was applied, or it appeared."""
    anchor = None
    for event in list_events(conn, region_id=region_id, limit=100_000):
        raised = (
            event.kind == "light_changed"
            and event.payload.get("source") == "adjust_light"
            and event.payload["after"] > event.payload["before"]
        )
        # A "neglect" event carries the city day it was applied for.
        if raised or event.kind in ("region_added", "neglect"):
            anchor = _event_day(event.created_at, event.payload)
    return anchor


def _neglect(conn: sqlite3.Connection, content: Content, day: date) -> list[str]:
    notes = []
    for region_id in content.regions:
        anchor = _last_cared_for(conn, region_id)
        if anchor is None or (day - anchor).days < NEGLECT_DAYS:
            continue
        region = world.get_region(conn, region_id)
        if region.fallen:
            continue
        change = apply_neglect(region.light, 1)
        world.apply_light_change(
            conn, region_id, change, SYSTEM, "nobody kept it lit this week", source="neglect"
        )
        # Stamp the city day so catch-up ticks measure the next week from it.
        append_event(conn, "neglect", SYSTEM, {"city_day": day.isoformat()}, region_id=region_id)
        notes.append(f"{region.name} dimmed from neglect ({change.before} -> {change.after})")
    return notes


def _advance_goals(conn: sqlite3.Connection, content: Content) -> list[str]:
    notes = []
    for npc in content.npcs.values():
        row = conn.execute(
            "SELECT stage, days_since FROM npc_goals WHERE npc_id = ?", (npc.id,)
        ).fetchone()
        stage, days = (row[0], row[1]) if row else (0, 0)
        days += 1
        if stage < len(npc.goal.stages) and days >= npc.goal.days_per_stage:
            stage, days = stage + 1, 0
            text = npc.goal.stages[stage - 1]
            region = content.locations[npc.location].region_id
            append_event(
                conn,
                "npc_goal_advanced",
                SYSTEM,
                {
                    "npc_id": npc.id,
                    "name": npc.name,
                    "goal": npc.goal.text,
                    "stage": stage,
                    "now": text,
                },
                region_id=region,
            )
            notes.append(f"{npc.name} {text}")
        conn.execute(
            "INSERT INTO npc_goals (npc_id, stage, days_since) VALUES (?, ?, ?)"
            " ON CONFLICT (npc_id) DO UPDATE SET stage = excluded.stage,"
            " days_since = excluded.days_since",
            (npc.id, stage, days),
        )
    return notes


def run_due_ticks(conn: sqlite3.Connection, content: Content, now: datetime) -> list[str]:
    """Run the tick for every city day since the last one, up to today. Idempotent."""
    today = date.fromisoformat(city_day(now))
    last = conn.execute("SELECT MAX(city_day) FROM city_ticks").fetchone()[0]
    if last is None:
        days = [today]
    else:
        first = max(
            date.fromisoformat(last) + timedelta(days=1),
            today - timedelta(days=MAX_CATCH_UP_DAYS - 1),
        )
        days = [first + timedelta(days=n) for n in range((today - first).days + 1)]
    notes: list[str] = []
    for day in days:
        with atomic(conn):
            notes += _neglect(conn, content, day)
            notes += _advance_goals(conn, content)
            conn.execute("INSERT INTO city_ticks (city_day) VALUES (?)", (day.isoformat(),))
    return notes
