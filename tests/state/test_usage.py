import sqlite3

import pytest

from new_vesper.state.errors import StateError
from new_vesper.state.events import SYSTEM
from new_vesper.state.scenes import open_scene
from new_vesper.state.usage import record_usage, usage_totals


def test_totals_per_player_and_overall(conn: sqlite3.Connection) -> None:
    scene = open_scene(conn, "market", SYSTEM)
    record_usage(
        conn,
        call_type="narration",
        model="haiku",
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=900,
        cost_micro_usd=120,
        player_id=1,
        scene_id=scene.id,
    )
    record_usage(
        conn,
        call_type="adjudication",
        model="sonnet",
        input_tokens=200,
        output_tokens=80,
        cost_micro_usd=500,
        player_id=2,
    )
    everyone = usage_totals(conn, "2000-01-01T00:00:00Z")
    assert (everyone.calls, everyone.input_tokens, everyone.cost_micro_usd) == (2, 300, 620)
    mine = usage_totals(conn, "2000-01-01T00:00:00Z", player_id=1)
    assert (mine.calls, mine.cache_read_tokens, mine.cost_micro_usd) == (1, 900, 120)
    assert usage_totals(conn, "2999-01-01T00:00:00Z").calls == 0


@pytest.mark.parametrize(
    "override",
    [
        {"input_tokens": -1},
        {"output_tokens": 1.5},
        {"cost_micro_usd": True},
        {"player_id": 999},
        {"player_id": 0},
        {"call_type": ""},
    ],
)
def test_bad_usage_rejected(conn: sqlite3.Connection, override: dict[str, object]) -> None:
    args: dict[str, object] = {
        "call_type": "narration",
        "model": "haiku",
        "input_tokens": 1,
        "output_tokens": 1,
        "cost_micro_usd": 1,
    }
    with pytest.raises(StateError):
        record_usage(conn, **{**args, **override})  # type: ignore[arg-type]
    assert usage_totals(conn, "2000-01-01T00:00:00Z").calls == 0
