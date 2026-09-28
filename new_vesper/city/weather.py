"""The weather right now in a district, generated block by block and stored (D51)."""

import random
import sqlite3
from datetime import datetime, timedelta

from new_vesper.budget.policy import stamp
from new_vesper.city.sky import season
from new_vesper.content.loader import Content
from new_vesper.content.model import SeasonWeather, WeatherState
from new_vesper.rules.clock import weather_block_start
from new_vesper.rules.weather import next_weather

# If nobody has looked at the weather for longer than this, walk only this many
# blocks forward from the default state rather than replaying every block.
MAX_CATCH_UP_BLOCKS = 16


def _block_rng(region_id: str, block: datetime) -> random.Random:
    """The same seed for the same district and block, so the sky is reproducible."""
    return random.Random(f"{region_id}|{stamp(block)}")


def previous_block(block: datetime) -> datetime:
    """The block before this one: the block holding the minute before it starts.

    Safe across daylight saving, where a block can be 2 or 4 real hours long.
    """
    return weather_block_start(block - timedelta(minutes=1))


def current_weather(
    conn: sqlite3.Connection, content: Content, region_id: str, now: datetime
) -> WeatherState:
    """The weather for this district's current block, generated and stored if new.

    Each new block follows from the last stored one through the district's
    transition table, so the weather drifts rather than jumps.
    """
    weather = content.regions[region_id].weather
    target = weather_block_start(now)
    target_stamp = stamp(target)
    row = conn.execute(
        "SELECT weather_id FROM weather WHERE region_id = ? AND block_start = ?",
        (region_id, target_stamp),
    ).fetchone()
    if row is not None and row[0] in weather.states:
        return weather.states[row[0]]
    last = conn.execute(
        "SELECT block_start, weather_id FROM weather WHERE region_id = ? AND block_start < ?"
        " ORDER BY block_start DESC LIMIT 1",
        (region_id, target_stamp),
    ).fetchone()
    blocks = [target]
    while len(blocks) < MAX_CATCH_UP_BLOCKS:
        earlier = previous_block(blocks[0])
        if last is not None and stamp(earlier) <= last[0]:
            break
        blocks.insert(0, earlier)
    state = last[1] if last is not None else None
    for block in blocks:
        table = _season_table(content, region_id, block)
        # A new season starts from its own weather if the old weather has no place in it.
        current = state if state in table.transitions else table.start
        state = next_weather(current, table.transitions, _block_rng(region_id, block))
        conn.execute(
            "INSERT OR IGNORE INTO weather (region_id, block_start, weather_id) VALUES (?, ?, ?)",
            (region_id, stamp(block), state),
        )
    stored = conn.execute(
        "SELECT weather_id FROM weather WHERE region_id = ? AND block_start = ?",
        (region_id, target_stamp),
    ).fetchone()
    return weather.states[stored[0]]


def _season_table(content: Content, region_id: str, block: datetime) -> SeasonWeather:
    weather = content.regions[region_id].weather
    current = season(content, block)
    if current is None:
        return next(iter(weather.seasons.values()))
    return weather.seasons[current.id]
