"""Recording every API call against the player and scene that triggered it."""

import sqlite3
from collections.abc import Mapping
from typing import Any

from new_vesper.budget.pricing import PRICES, ModelPrice, TokenUsage, cost_micro_usd
from new_vesper.dm.config import CallType
from new_vesper.state.usage import record_usage


def record_call(
    conn: sqlite3.Connection,
    call: CallType,
    model: str,
    usage: Any,
    *,
    player_id: int | None,
    scene_id: int | None,
    prices: Mapping[str, ModelPrice] = PRICES,
) -> int:
    """Price one call and append it to the usage ledger. Returns its cost in micro-dollars."""
    tokens = TokenUsage.from_response(usage)
    cost = cost_micro_usd(model, tokens, prices)
    record_usage(
        conn,
        call_type=call.value,
        model=model,
        input_tokens=tokens.input_tokens,
        output_tokens=tokens.output_tokens,
        cache_read_tokens=tokens.cache_read_tokens,
        cache_write_tokens=tokens.cache_write_tokens,
        cost_micro_usd=cost,
        player_id=player_id,
        scene_id=scene_id,
    )
    return cost
