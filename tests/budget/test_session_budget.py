"""Budget enforcement inside the play loop, with a stubbed model."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from new_vesper.budget.policy import BudgetConfig, stamp
from new_vesper.content.loader import Content
from new_vesper.dm.session import PlaySession, SessionError
from new_vesper.state import characters, scenes
from tests.dm.conftest import (
    DESIGN_TEXT,
    NOON_TUESDAY,
    SeqRng,
    StubClient,
    make_character,
    say,
    use,
)

TINY = BudgetConfig(monthly_cap_micro=50_000_000, player_allowance_micro=5_000)


def ledger(conn: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return conn.execute(
        "SELECT player_id, scene_id, call_type, model, cost_micro_usd FROM usage_ledger ORDER BY id"
    ).fetchall()


def test_every_call_is_recorded_against_player_and_scene(
    conn: sqlite3.Connection, content: Content
) -> None:
    char = make_character(conn, online=False)
    client = StubClient(say("Open."), use(("look", {"entity": "me"})), say("Done."))
    # Noon on a Tuesday, so Tomás and Vasil are on Tarp Row: not the real clock, which
    # empties the Row on a Sunday afternoon.
    play = PlaySession(
        conn, content, client, DESIGN_TEXT, SeqRng(), char.id, now=lambda: NOON_TUESDAY
    )
    play.start()
    play.turn("I look myself over")
    rows = ledger(conn)
    assert len(rows) == len(client.messages.calls)
    assert {r[0] for r in rows} == {char.player_id}
    assert {r[1] for r in rows} == {play.scene_id}
    # Each turn with NPCs present ends with a cheap read of what they learned (D123).
    assert [r[2] for r in rows] == [
        "turn",
        "beat_summary",
        "npc_facts",
        "turn",
        "turn",
        "beat_summary",
        "npc_facts",
    ]
    # Stub usage is 100 in / 50 out: Sonnet $2/$10 -> 700; Haiku $1/$5 -> 350.
    assert [r[4] for r in rows] == [700, 350, 350, 700, 700, 350, 350]


def test_spent_allowance_blocks_start(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    conn.execute(
        "INSERT INTO usage_ledger (player_id, call_type, model, input_tokens, output_tokens,"
        " cost_micro_usd) VALUES (?, 'turn', 'm', 0, 0, 10000000)",
        (char.player_id,),
    )
    client = StubClient()
    play = PlaySession(conn, content, client, DESIGN_TEXT, SeqRng(), char.id)
    with pytest.raises(SessionError, match="Your share"):
        play.start()
    assert client.messages.calls == []
    assert not characters.get_character(conn, char.id).online


def test_running_out_mid_turn_goes_quiet(conn: sqlite3.Connection, content: Content) -> None:
    """The turn stops before the call that would pass the limit; completed writes stand."""
    char = make_character(conn, online=False)

    def after_roll(kwargs: dict[str, Any]) -> Any:
        rid = json.loads(kwargs["messages"][-1]["content"][0]["content"])["roll_id"]
        return use(
            (
                "apply_consequence",
                {"roll_id": rid, "type": "deal_harm", "target": "me", "magnitude": 2},
            )
        )

    client = StubClient(
        say("Open."),
        use(("call_for_roll", {"stat": "slick", "difficulty": "risky", "stakes": "run"})),
        after_roll,
        say("never reached"),
    )
    # Opening (700) + summary (350) + two turn calls (1400) = 2450; the third turn call is blocked.
    budget = BudgetConfig(player_allowance_micro=2_450)
    play = PlaySession(conn, content, client, DESIGN_TEXT, SeqRng(1, 2), char.id, budget=budget)
    play.start()
    outcome = play.turn("I run for it")
    assert outcome.quiet
    assert "city goes quiet" in outcome.narration or "Your share" in outcome.narration
    assert play.character.sheet.harm == 2  # the consequence already applied stands
    assert len(client.messages.turn_calls) == 3
    assert conn.execute("SELECT COUNT(*) FROM beats WHERE status = 'open'").fetchone()[0] == 0
    [_, beat] = scenes.recent_beats(conn, play.scene_id)
    assert beat.summary == outcome.narration[:200]
    with pytest.raises(SessionError, match="Your share"):
        play.turn("I try again")
    with pytest.raises(SessionError):
        play.go("umbrella-shrine")


def test_the_city_stirs_again_next_month(conn: sqlite3.Connection, content: Content) -> None:
    char = make_character(conn, online=False)
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO usage_ledger (player_id, call_type, model, input_tokens, output_tokens,"
        " cost_micro_usd, created_at) VALUES (NULL, 'turn', 'm', 0, 0, 60000000, ?)",
        (stamp(now),),
    )
    blocked = PlaySession(
        conn, content, StubClient(), DESIGN_TEXT, SeqRng(), char.id, now=lambda: now
    )
    with pytest.raises(SessionError, match="gone quiet"):
        blocked.start()
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=2)
    later = PlaySession(
        conn,
        content,
        StubClient(say("Morning.")),
        DESIGN_TEXT,
        SeqRng(),
        char.id,
        now=lambda: next_month,
    )
    assert later.start()[2].narration == "Morning."


def test_session_refuses_unpriced_models(conn: sqlite3.Connection, content: Content) -> None:
    from new_vesper.budget.pricing import UnpricedModel
    from new_vesper.dm.config import DMConfig

    char = make_character(conn, online=False)
    with pytest.raises(UnpricedModel):
        PlaySession(
            conn,
            content,
            StubClient(),
            DESIGN_TEXT,
            SeqRng(),
            char.id,
            config=DMConfig(summary_model="claude-mystery-9"),
        )
