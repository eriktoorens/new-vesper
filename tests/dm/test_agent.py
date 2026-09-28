"""The tool loop, with a stubbed model client."""

from typing import Any

from new_vesper.dm.agent import REFUSAL_NARRATION, run_turn, summarize
from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.tools import TOOLS
from tests.dm.conftest import Response, StubClient, say, use

SYSTEM = [{"type": "text", "text": "sys", "cache_control": {"type": "ephemeral"}}]


def echo_dispatch(calls: list[tuple[str, Any]]):
    def dispatch(name: str, raw: Any) -> tuple[dict[str, Any], bool]:
        calls.append((name, raw))
        return ({"error": "nope"}, True) if name == "bad" else ({"ok": name}, False)

    return dispatch


def test_plain_narration() -> None:
    client = StubClient(say("Rain on the tarps."))
    result = run_turn(client, DMConfig(), SYSTEM, "hi", echo_dispatch([]))
    assert result.narration == "Rain on the tarps."
    [call] = client.messages.calls
    assert call["model"] == "claude-sonnet-5"
    assert call["tools"] is TOOLS
    assert call["output_config"] == {"effort": "medium"}


def test_tool_round_trip() -> None:
    client = StubClient(
        use(("look", {"entity": "me"}), ("bad", {"x": 1})),
        say("You look around."),
    )
    seen: list[tuple[str, Any]] = []
    result = run_turn(client, DMConfig(), SYSTEM, "hi", echo_dispatch(seen))
    assert result.narration == "You look around."
    assert seen == [("look", {"entity": "me"}), ("bad", {"x": 1})]
    second = client.messages.calls[1]["messages"]
    assert second[1]["role"] == "assistant"
    assert second[1]["content"][0].type == "thinking"  # whole assistant turn sent back
    results = second[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_0", "toolu_1"]
    assert [r["is_error"] for r in results] == [False, True]
    assert [c.is_error for c in result.tool_calls] == [False, True]


def test_rounds_are_capped() -> None:
    looping = [use(("look", {"entity": "me"})) for _ in range(10)]
    client = StubClient(*looping, say("Enough."))
    config = DMConfig(max_tool_rounds=3)
    result = run_turn(client, config, SYSTEM, "hi", echo_dispatch([]))
    calls = client.messages.calls
    assert len(calls) == 4
    assert calls[-1]["tool_choice"] == {"type": "none"}
    assert "tool_choice" not in calls[0]
    assert result.rounds == 4


def test_refusal_gets_a_safe_narration() -> None:
    client = StubClient(Response([], "refusal"))
    assert run_turn(client, DMConfig(), SYSTEM, "x", echo_dispatch([])).narration == (
        REFUSAL_NARRATION
    )


def test_usage_is_reported_per_call() -> None:
    seen: list[tuple[CallType, str]] = []
    client = StubClient(use(("look", {"entity": "me"})), say("ok"))
    run_turn(
        client,
        DMConfig(),
        SYSTEM,
        "hi",
        echo_dispatch([]),
        lambda call, model, usage: seen.append((call, model)),
    )
    summarize(
        client,
        DMConfig(),
        CallType.BEAT_SUMMARY,
        "sum",
        lambda call, model, usage: seen.append((call, model)),
    )
    assert seen == [
        (CallType.TURN, "claude-sonnet-5"),
        (CallType.TURN, "claude-sonnet-5"),
        (CallType.BEAT_SUMMARY, "claude-haiku-4-5"),
    ]


def test_tool_definitions_are_cached_and_closed() -> None:
    assert TOOLS[-1]["cache_control"] == {"type": "ephemeral"}
    assert sum("cache_control" in t for t in TOOLS) == 1
    assert {t["name"] for t in TOOLS} == {
        "look",
        "call_for_roll",
        "apply_consequence",
        "grant_from_table",
        "report_trigger",
        "adjust_light",
        "adjust_attitude",
        "create_encounter",
    }
    assert all(t["input_schema"]["additionalProperties"] is False for t in TOOLS)


def test_config_from_env() -> None:
    config = DMConfig.from_env({"NEW_VESPER_TURN_MODEL": "claude-opus-5"})
    assert config.model_for(CallType.TURN) == "claude-opus-5"
    assert config.model_for(CallType.RECAP) == "claude-haiku-4-5"
