"""The monthly cap (D21), the per-player allowance (D22) and the month boundary.

Both limits are operator settings, enforced on recorded spend. Months are UTC
calendar months, matching the time model (D9).
"""

import os
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from itertools import pairwise

from new_vesper.state.usage import usage_totals

MICRO_PER_USD = 1_000_000
# Calls closer together than this count as continuous play.
IDLE_GAP_SECONDS = 600
# Below this much measured play, a cost-per-hour estimate means little.
MIN_HOURS_FOR_ESTIMATE = 0.05


class BudgetExhausted(Exception):
    """Spending would pass a limit. The message is shown to the player."""


@dataclass(frozen=True)
class BudgetConfig:
    monthly_cap_micro: int = 50 * MICRO_PER_USD
    player_allowance_micro: int = 10 * MICRO_PER_USD

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "BudgetConfig":
        """NEW_VESPER_MONTHLY_CAP_USD and NEW_VESPER_PLAYER_ALLOWANCE_USD, in dollars."""
        base = cls()
        return cls(
            monthly_cap_micro=_usd(env.get("NEW_VESPER_MONTHLY_CAP_USD"), base.monthly_cap_micro),
            player_allowance_micro=_usd(
                env.get("NEW_VESPER_PLAYER_ALLOWANCE_USD"), base.player_allowance_micro
            ),
        )


def _usd(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"not a dollar amount: {value!r}") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"a budget must be a non-negative dollar amount, got {value!r}")
    return int(amount * MICRO_PER_USD)


def month_start(now: datetime) -> datetime:
    now = now.astimezone(UTC)
    return datetime(now.year, now.month, 1, tzinfo=UTC)


def next_reset(now: datetime) -> datetime:
    start = month_start(now)
    if start.month == 12:
        return start.replace(year=start.year + 1, month=1)
    return start.replace(month=start.month + 1)


def stamp(moment: datetime) -> str:
    """The ledger's timestamp format, so string comparison orders correctly."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def usd(micro: int, *, round_down: bool = False) -> str:
    """Dollars to the cent. Money left rounds down, so it is never overstated."""
    cents = micro // 10_000 if round_down else round(micro / 10_000)
    return f"${cents // 100:,}.{cents % 100:02d}"


def active_hours(conn: sqlite3.Connection, player_id: int, since: str | None = None) -> float:
    """Measured play time: the gaps between a player's calls, ignoring idle breaks."""
    sql = "SELECT created_at FROM usage_ledger WHERE player_id = ?"
    params: list[object] = [player_id]
    if since is not None:
        sql += " AND created_at >= ?"
        params.append(since)
    times = [
        datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        for row in conn.execute(sql + " ORDER BY created_at", params)
    ]
    seconds = 0.0
    for earlier, later in pairwise(times):
        gap = (later - earlier).total_seconds()
        if gap <= IDLE_GAP_SECONDS:
            seconds += gap
    return seconds / 3600


def cost_per_hour_micro(conn: sqlite3.Connection, player_id: int) -> int | None:
    """This player's measured cost per hour of play, over their whole history."""
    hours = active_hours(conn, player_id)
    if hours < MIN_HOURS_FOR_ESTIMATE:
        return None
    spent = usage_totals(conn, "0000", player_id=player_id).cost_micro_usd
    return round(spent / hours)


@dataclass(frozen=True)
class BudgetStatus:
    city_spent: int
    city_cap: int
    player_spent: int
    player_allowance: int
    reset_at: datetime
    player_cost_per_hour: int | None

    @property
    def city_quiet(self) -> bool:
        return self.city_spent >= self.city_cap

    @property
    def player_exhausted(self) -> bool:
        return self.player_spent >= self.player_allowance

    @property
    def can_play(self) -> bool:
        return not (self.city_quiet or self.player_exhausted)

    @property
    def player_remaining(self) -> int:
        return max(0, self.player_allowance - self.player_spent)

    @property
    def hours_left(self) -> float | None:
        """The allowance left, as hours at this player's own measured rate (D22)."""
        if not self.player_cost_per_hour:
            return None
        return self.player_remaining / self.player_cost_per_hour

    def blocked_message(self) -> str:
        when = f"{self.reset_at:%B} {self.reset_at.day}"
        if self.city_quiet:
            return (
                "The city has gone quiet: this month's attention is spent. "
                f"It stirs again on {when} (UTC)."
            )
        return f"Your share of the city's attention is spent for this month. It returns on {when}."

    def allowance_message(self) -> str:
        left = usd(self.player_remaining, round_down=True)
        hours = self.hours_left
        estimate = f", about {hours:.1f} hours of play" if hours is not None else ""
        return f"Allowance left this month: {left}{estimate}."


def budget_status(
    conn: sqlite3.Connection, config: BudgetConfig, player_id: int, now: datetime
) -> BudgetStatus:
    since = stamp(month_start(now))
    return BudgetStatus(
        city_spent=usage_totals(conn, since).cost_micro_usd,
        city_cap=config.monthly_cap_micro,
        player_spent=usage_totals(conn, since, player_id=player_id).cost_micro_usd,
        player_allowance=config.player_allowance_micro,
        reset_at=next_reset(now),
        player_cost_per_hour=cost_per_hour_micro(conn, player_id),
    )
