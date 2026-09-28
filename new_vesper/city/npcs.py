"""Where NPCs are right now, from their schedules (D52)."""

from dataclasses import dataclass
from datetime import datetime

from new_vesper.content.loader import Content
from new_vesper.content.model import NpcDef
from new_vesper.rules.clock import minutes_into_day, weekday


@dataclass(frozen=True)
class Whereabouts:
    npc: NpcDef
    location: str | None  # None: away from the district
    activity: str


def whereabouts(npc: NpcDef, now: datetime) -> Whereabouts:
    """Where this NPC is at this instant: today's schedule if it differs, else the default."""
    blocks = npc.schedule.get(weekday(now), npc.schedule["default"])
    minute = minutes_into_day(now)
    block = next(b for b in blocks if b.covers(minute))
    return Whereabouts(npc, block.location, block.activity)


def present_at(content: Content, location_id: str, now: datetime) -> list[Whereabouts]:
    """Everyone whose schedule puts them here right now."""
    return [
        where
        for npc in content.npcs.values()
        if (where := whereabouts(npc, now)).location == location_id
    ]


def regulars_elsewhere(content: Content, location_id: str, now: datetime) -> list[Whereabouts]:
    """NPCs whose home is here but who are somewhere else right now."""
    return [
        where
        for npc in content.npcs.values()
        if npc.location == location_id and (where := whereabouts(npc, now)).location != location_id
    ]
