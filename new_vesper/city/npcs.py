"""Where NPCs are (D111-D113, D132-D134): stored, one place at a time, with the schedule
as an agenda.

An NPC nobody is with follows their agenda (D113). An NPC who is where a player
character is stays until the story has them go (D112); code reads that from the
narration after each turn (D132). They may go where their agenda says, or where a
want takes them: a detour that lasts until their next scheduled block, two hours at
most, before they rejoin their day (D133).
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from new_vesper.content.loader import Content
from new_vesper.content.model import NpcDef
from new_vesper.rules.clock import minutes_into_day, weekday
from new_vesper.rules.sky import moon
from new_vesper.state import npc_whereabouts as stored
from new_vesper.state.events import SYSTEM, Cause, append_event


@dataclass(frozen=True)
class Agenda:
    """What an NPC's day calls for at a moment (D52)."""

    npc: NpcDef
    location: str | None  # None: away from the district
    activity: str
    starts: int  # minutes after city midnight that this part of their day began


@dataclass(frozen=True)
class Whereabouts:
    """Where an NPC really is, and what their day calls for now."""

    npc: NpcDef
    location: str | None  # None: away from the district
    activity: str
    since: datetime
    agenda: Agenda

    @property
    def on_agenda(self) -> bool:
        return (self.location, self.activity) == (self.agenda.location, self.agenda.activity)


def agenda(npc: NpcDef, now: datetime) -> Agenda:
    """What this NPC means to be doing at this instant.

    A moon-day schedule (new or full moon) wins over a weekday, which wins over the default.
    """
    phase = moon(now).phase.replace(" ", "-")  # "new moon" -> "new-moon"
    blocks = npc.schedule.get(phase) or npc.schedule.get(weekday(now)) or npc.schedule["default"]
    minute = minutes_into_day(now)
    block = next(b for b in blocks if b.covers(minute))
    return Agenda(npc, block.location, block.activity, block.start)


def settle(
    conn: sqlite3.Connection, content: Content, now: datetime, arriving: int | None = None
) -> None:
    """Bring every NPC nobody is with up to their agenda (D113).

    An NPC where a player character is stays put until the Narrator moves them on (D112).
    ``arriving`` is a character coming online: not yet with anyone, even if a lost
    connection left them marked online.
    """
    watched = stored.watched_locations(conn, excluding=arriving)
    current = stored.all_whereabouts(conn)
    for npc in content.npcs.values():
        plan = agenda(npc, now)
        was = current.get(npc.id)
        if was is not None and was.detour_until is not None and now < was.detour_until:
            continue  # off their agenda for a while, because they wanted to be (D133)
        if was is not None and (was.location_id, was.activity) == (plan.location, plan.activity):
            if was.detour_until is not None:
                stored.put(conn, npc.id, plan.location, plan.activity, was.since)
            continue
        if was is not None and was.location_id in watched:
            continue
        stored.put(conn, npc.id, plan.location, plan.activity, now)
        if was is not None and was.location_id != plan.location:
            append_event(
                conn,
                "npc_moved",
                SYSTEM,
                {"npc_id": npc.id, "from": was.location_id, "to": plan.location},
            )


def everyone(conn: sqlite3.Connection, content: Content, now: datetime) -> list[Whereabouts]:
    """Every NPC, where they really are, in content order."""
    settle(conn, content, now)
    current = stored.all_whereabouts(conn)
    return [
        Whereabouts(npc, was.location_id, was.activity, was.since, agenda(npc, now))
        for npc in content.npcs.values()
        if (was := current.get(npc.id)) is not None
    ]


def where_is(conn: sqlite3.Connection, content: Content, npc_id: str, now: datetime) -> Whereabouts:
    return next(w for w in everyone(conn, content, now) if w.npc.id == npc_id)


def present_at(
    conn: sqlite3.Connection, content: Content, location_id: str, now: datetime
) -> list[Whereabouts]:
    """Everyone who is here right now."""
    return [w for w in everyone(conn, content, now) if w.location == location_id]


def regulars_elsewhere(
    conn: sqlite3.Connection, content: Content, location_id: str, now: datetime
) -> list[Whereabouts]:
    """NPCs whose home is here but who are somewhere else right now."""
    return [
        w
        for w in everyone(conn, content, now)
        if w.npc.location == location_id and w.location != location_id
    ]


# The longest an NPC stays off their agenda for a want (D133).
MAX_DETOUR = timedelta(hours=2)


def detour_ends(npc: NpcDef, now: datetime) -> datetime:
    """When the NPC's day next calls them to something new, or two hours on, if sooner."""
    plan = agenda(npc, now)
    for minutes in range(1, int(MAX_DETOUR.total_seconds() // 60)):
        later = now + timedelta(minutes=minutes)
        nxt = agenda(npc, later)
        if (nxt.location, nxt.activity) != (plan.location, plan.activity):
            return later
    return now + MAX_DETOUR


def go(
    conn: sqlite3.Connection,
    content: Content,
    npc_id: str,
    to: str | None,
    now: datetime,
    cause: Cause,
    reason: str,
) -> tuple[Whereabouts, Whereabouts]:
    """An NPC goes somewhere because the story had them go (D132).

    Where their agenda says, they simply take up their day; anywhere else is a detour
    (D133). ``to`` None is away from the district. The caller checks they may.
    """
    before = where_is(conn, content, npc_id, now)
    plan = before.agenda
    if to == plan.location:
        stored.put(conn, npc_id, plan.location, plan.activity, now)
        until = None
    else:
        until = detour_ends(before.npc, now)
        stored.put(conn, npc_id, to, reason[:200], now, until)
    append_event(
        conn,
        "npc_went",
        cause,
        {
            "npc_id": npc_id,
            "from": before.location,
            "to": to,
            "reason": reason,
            "detour_until": None if until is None else until.isoformat(),
        },
    )
    return before, where_is(conn, content, npc_id, now)
