import sqlite3
from datetime import UTC, datetime, timedelta

from new_vesper.budget.policy import BudgetConfig, stamp
from new_vesper.budget.report import month_report
from new_vesper.state import players
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM


def test_month_report() -> None:
    conn: sqlite3.Connection = open_database()
    players.create_player(conn, "ash", SYSTEM)
    now = datetime(2026, 9, 28, 12, tzinfo=UTC)
    for minutes in range(0, 31, 5):
        conn.execute(
            "INSERT INTO usage_ledger (player_id, call_type, model, input_tokens, output_tokens,"
            " cost_micro_usd, created_at) VALUES (1, 'turn', 'm', 0, 0, 100000, ?)",
            (stamp(now - timedelta(hours=1) + timedelta(minutes=minutes)),),
        )
    lines = month_report(conn, BudgetConfig(), now)
    assert lines[0] == "Month from 2026-09-01 (resets 2026-10-01, UTC)"
    assert lines[1] == "City: $0.70 of $50.00 cap over 7 calls"
    assert lines[2] == "  ash: $0.70 of $10.00, 0.50 hours played, $1.40/hour"
    assert lines[3] == "Cost per player-hour this month: $1.40"
