import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from new_vesper.budget.policy import (
    BudgetConfig,
    active_hours,
    budget_status,
    month_start,
    next_reset,
    stamp,
)
from new_vesper.state import players
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    db = open_database()
    players.create_player(db, "ash", SYSTEM)
    players.create_player(db, "bo", SYSTEM)
    yield db
    db.close()


def spend(conn: sqlite3.Connection, player_id: int | None, micro: int, when: datetime) -> None:
    conn.execute(
        "INSERT INTO usage_ledger (player_id, call_type, model, input_tokens, output_tokens,"
        " cost_micro_usd, created_at) VALUES (?, 'turn', 'claude-sonnet-5', 0, 0, ?, ?)",
        (player_id, micro, stamp(when)),
    )


def test_month_boundaries() -> None:
    assert month_start(NOW) == datetime(2026, 9, 1, tzinfo=UTC)
    assert next_reset(NOW) == datetime(2026, 10, 1, tzinfo=UTC)
    december = datetime(2026, 12, 31, 23, 59, tzinfo=UTC)
    assert next_reset(december) == datetime(2027, 1, 1, tzinfo=UTC)


def test_defaults_are_the_decided_limits() -> None:
    config = BudgetConfig()
    assert (config.monthly_cap_micro, config.player_allowance_micro) == (50_000_000, 10_000_000)


def test_limits_from_env() -> None:
    config = BudgetConfig.from_env(
        {"NEW_VESPER_MONTHLY_CAP_USD": "12.50", "NEW_VESPER_PLAYER_ALLOWANCE_USD": "0"}
    )
    assert (config.monthly_cap_micro, config.player_allowance_micro) == (12_500_000, 0)


@pytest.mark.parametrize("value", ["lots", "-5", "nan", "inf"])
def test_bad_env_limits_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        BudgetConfig.from_env({"NEW_VESPER_MONTHLY_CAP_USD": value})


def test_only_this_month_counts(conn: sqlite3.Connection) -> None:
    spend(conn, 1, 9_000_000, datetime(2026, 8, 31, 23, 0, tzinfo=UTC))
    spend(conn, 1, 1_000_000, datetime(2026, 9, 2, tzinfo=UTC))
    status = budget_status(conn, BudgetConfig(), 1, NOW)
    assert (status.player_spent, status.city_spent) == (1_000_000, 1_000_000)
    assert status.can_play
    assert status.reset_at == datetime(2026, 10, 1, tzinfo=UTC)


def test_player_allowance_blocks_only_that_player(conn: sqlite3.Connection) -> None:
    spend(conn, 1, 10_000_000, NOW - timedelta(hours=1))
    ash, bo = (budget_status(conn, BudgetConfig(), p, NOW) for p in (1, 2))
    assert ash.player_exhausted and not ash.can_play
    assert "Your share" in ash.blocked_message()
    assert bo.can_play


def test_city_cap_blocks_everyone(conn: sqlite3.Connection) -> None:
    for player in (1, 2, None):
        spend(conn, player, 16_700_000, NOW - timedelta(hours=1))
    for player in (1, 2):
        status = budget_status(conn, BudgetConfig(player_allowance_micro=10**9), player, NOW)
        assert status.city_quiet and not status.can_play
        assert "October 1" in status.blocked_message()


def test_active_hours_skip_idle_breaks(conn: sqlite3.Connection) -> None:
    start = datetime(2026, 9, 10, 20, 0, tzinfo=UTC)
    for minutes in (0, 5, 10, 15, 120, 125):  # a 105-minute break between sittings
        spend(conn, 1, 1000, start + timedelta(minutes=minutes))
    assert active_hours(conn, 1) == pytest.approx(20 / 60)


def test_hours_left_uses_the_players_own_rate(conn: sqlite3.Connection) -> None:
    start = NOW - timedelta(hours=2)
    for minutes in range(0, 61, 5):  # one hour of play, $1 spent
        spend(conn, 1, 1_000_000 // 13, start + timedelta(minutes=minutes))
    status = budget_status(conn, BudgetConfig(), 1, NOW)
    assert status.hours_left == pytest.approx(9.0, rel=0.01)
    assert "about 9.0 hours" in status.allowance_message()


def test_no_estimate_without_enough_play(conn: sqlite3.Connection) -> None:
    spend(conn, 1, 100, NOW)
    status = budget_status(conn, BudgetConfig(), 1, NOW)
    assert status.hours_left is None
    assert status.allowance_message() == "Allowance left this month: $9.99."


def test_dollars_display() -> None:
    from new_vesper.budget.policy import usd

    assert usd(1_234_567_890) == "$1,234.57"
    assert usd(9_998_950) == "$10.00"
    assert usd(9_998_950, round_down=True) == "$9.99"
    assert usd(0) == "$0.00"
