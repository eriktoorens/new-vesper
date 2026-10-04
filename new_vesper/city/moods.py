"""Each NPC's mood for the city day (D119): rolled by code, the same for everyone.

Their goal moving on today colors it first; cold or hot weather often does.
The Narrator may shift it within a scene (``npc_mood``).
"""

import random
import sqlite3
from datetime import datetime

from new_vesper.city.weather import current_weather
from new_vesper.content.loader import Content
from new_vesper.content.model import NpcDef
from new_vesper.rules.clock import city_day
from new_vesper.state import npc_minds
from new_vesper.state.npc_minds import Mood

# How often cold or hot weather sets the day's mood, when it can.
FOUL_WEATHER_CHANCE = 0.5


def _goal_moved_today(conn: sqlite3.Connection, npc_id: str) -> bool:
    row = conn.execute(
        "SELECT stage, days_since FROM npc_goals WHERE npc_id = ?", (npc_id,)
    ).fetchone()
    return row is not None and row[0] > 0 and row[1] == 0


def roll_mood(npc: NpcDef, day: str, goal_moved: bool, foul: bool) -> str:
    """The day's mood: seeded by NPC and city day, so it is the same for everyone."""
    rng = random.Random(f"mood|{npc.id}|{day}")
    if goal_moved:
        return rng.choice(npc.moods.goal_news)
    if foul and rng.random() < FOUL_WEATHER_CHANCE:
        return rng.choice(npc.moods.foul_weather)
    return rng.choice(npc.moods.usual)


def mood_now(conn: sqlite3.Connection, content: Content, npc: NpcDef, now: datetime) -> Mood:
    """Today's mood: the latest the Narrator gave, or the one code rolled this morning."""
    day = city_day(now)
    found = npc_minds.mood_today(conn, npc.id, day)
    if found is not None:
        return found
    region = content.locations[npc.location].region_id
    foul = current_weather(conn, content, region, now).exposure is not None
    mood = roll_mood(npc, day, _goal_moved_today(conn, npc.id), foul)
    return npc_minds.add_mood(conn, npc.id, day, mood, "rolled")
