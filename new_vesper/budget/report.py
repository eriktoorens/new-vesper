"""An operator's view of the month: spend against the cap, per player, per hour."""

import sqlite3
from datetime import datetime

from new_vesper.budget.policy import (
    BudgetConfig,
    active_hours,
    month_start,
    next_reset,
    stamp,
    usd,
)
from new_vesper.state.usage import usage_totals


def month_report(conn: sqlite3.Connection, config: BudgetConfig, now: datetime) -> list[str]:
    since = stamp(month_start(now))
    city = usage_totals(conn, since)
    lines = [
        f"Month from {since[:10]} (resets {next_reset(now):%Y-%m-%d}, UTC)",
        f"City: {usd(city.cost_micro_usd)} of {usd(config.monthly_cap_micro)} cap"
        f" over {city.calls} calls",
    ]
    total_hours = 0.0
    rows = conn.execute(
        "SELECT p.id, p.handle, COALESCE(SUM(u.cost_micro_usd), 0)"
        " FROM players p JOIN usage_ledger u ON u.player_id = p.id"
        " WHERE u.created_at >= ? GROUP BY p.id ORDER BY 3 DESC",
        (since,),
    ).fetchall()
    for player_id, handle, spent in rows:
        hours = active_hours(conn, player_id, since)
        total_hours += hours
        rate = f", {usd(round(spent / hours))}/hour" if hours >= 0.05 else ""
        lines.append(
            f"  {handle}: {usd(spent)} of {usd(config.player_allowance_micro)},"
            f" {hours:.2f} hours played{rate}"
        )
    if total_hours >= 0.05:
        lines.append(
            f"Cost per player-hour this month: {usd(round(city.cost_micro_usd / total_hours))}"
        )
    else:
        lines.append("Cost per player-hour: not enough play yet to estimate.")
    return lines
