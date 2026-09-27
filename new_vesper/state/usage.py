"""The usage ledger: token usage and cost for every API call. Append-only.

Usage rows are their own ledger, so they do not also go to the event log.
"""

import sqlite3
from dataclasses import dataclass

from new_vesper.rules.errors import require_int
from new_vesper.state.errors import StateError
from new_vesper.state.validate import as_state_error, row_id, text


@dataclass(frozen=True)
class UsageTotals:
    calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_micro_usd: int


def _count(value: object, name: str) -> int:
    with as_state_error():
        number = require_int(value, name)
    if number < 0:
        raise StateError(f"{name} must not be negative")
    return number


def record_usage(
    conn: sqlite3.Connection,
    *,
    call_type: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_micro_usd: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    player_id: int | None = None,
    scene_id: int | None = None,
) -> int:
    """Record one API call against the player and scene that triggered it."""
    values = (
        None if player_id is None else row_id(player_id, "player id"),
        None if scene_id is None else row_id(scene_id, "scene id"),
        text(call_type, "call type", 40),
        text(model, "model", 80),
        _count(input_tokens, "input tokens"),
        _count(output_tokens, "output tokens"),
        _count(cache_read_tokens, "cache read tokens"),
        _count(cache_write_tokens, "cache write tokens"),
        _count(cost_micro_usd, "cost"),
    )
    with as_state_error():
        cursor = conn.execute(
            "INSERT INTO usage_ledger (player_id, scene_id, call_type, model, input_tokens,"
            " output_tokens, cache_read_tokens, cache_write_tokens, cost_micro_usd)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
    return int(cursor.lastrowid or 0)


def usage_totals(
    conn: sqlite3.Connection, since: str, *, player_id: int | None = None
) -> UsageTotals:
    """Totals from ``since`` (an ISO-8601 UTC timestamp), for one player or everyone."""
    since_ts = text(since, "since", 40)
    sql = (
        "SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0),"
        " COALESCE(SUM(cache_read_tokens), 0), COALESCE(SUM(cache_write_tokens), 0),"
        " COALESCE(SUM(cost_micro_usd), 0) FROM usage_ledger WHERE created_at >= ?"
    )
    params: tuple[object, ...] = (since_ts,)
    if player_id is not None:
        sql += " AND player_id = ?"
        params = (since_ts, row_id(player_id, "player id"))
    return UsageTotals(*conn.execute(sql, params).fetchone())
