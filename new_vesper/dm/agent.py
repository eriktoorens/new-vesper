"""The DM agent: one turn is a manual tool-use loop over an injected model client.

The client only needs ``messages.create(**kwargs)``, so tests pass a stub and
the CLI passes ``anthropic.Anthropic()``. A manual loop (rather than the SDK's
beta tool runner) keeps every tool call going through handlers.dispatch with
this turn's context, and caps how many rounds a turn may take.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.prompt import SUMMARY_SYSTEM
from new_vesper.dm.tools import TOOLS

REFUSAL_NARRATION = (
    "The rain thickens and the moment won't come into focus. (The DM couldn't narrate that; "
    "try something else.)"
)
EMPTY_NARRATION = "The city holds its breath. Nothing seems to change."


class Messages(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class ModelClient(Protocol):
    messages: Messages


# (call type, model, usage object from the response)
UsageHook = Callable[[CallType, str, Any], None]
# Called before every model call; raises to stop spending (e.g. BudgetExhausted).
Guard = Callable[[], None]
# Called with the draft narration when the model wants to end its turn; returns a
# reminder if it may not end yet.
Completion = Callable[[str], str | None]
# How many times a turn is sent back for unfinished business before it may end anyway.
MAX_REMINDERS = 2
# (tool name, raw input) -> (result, is_error)
Dispatch = Callable[[str, Any], tuple[dict[str, Any], bool]]


@dataclass
class ToolCall:
    name: str
    input: Any
    result: dict[str, Any]
    is_error: bool


@dataclass
class TurnResult:
    narration: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None
    rounds: int = 0


def _text_of(response: Any) -> str:
    return "\n\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def run_turn(
    client: ModelClient,
    config: DMConfig,
    system: list[dict[str, Any]],
    user_content: str,
    dispatch: Dispatch,
    on_usage: UsageHook | None = None,
    guard: Guard | None = None,
    *,
    tools: list[dict[str, Any]] | None = None,
    completion: Completion | None = None,
) -> TurnResult:
    """Run the model until it narrates. Tools are executed through ``dispatch`` only.

    ``guard`` runs before every model call and may raise to stop the turn; tool
    calls already made stay applied, since each one is complete on its own.
    ``completion`` runs when the model tries to finish; if it returns a reminder
    (for example, a roll that still owes its consequence), the model is sent back.
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
    turn = TurnResult(narration="")
    params: dict[str, Any] = {
        "model": config.turn_model,
        "max_tokens": config.turn_max_tokens,
        "system": system,
        "tools": TOOLS if tools is None else tools,
    }
    reminders = 0
    if config.turn_effort:
        params["output_config"] = {"effort": config.turn_effort}
    for round_number in range(config.max_tool_rounds + 1):
        last_round = round_number == config.max_tool_rounds
        # Out of rounds: the model must narrate with what it has.
        extra = {"tool_choice": {"type": "none"}} if last_round else {}
        if guard is not None:
            guard()
        response = client.messages.create(**params, **extra, messages=messages)
        turn.rounds = round_number + 1
        turn.stop_reason = response.stop_reason
        if on_usage is not None:
            on_usage(CallType.TURN, config.turn_model, response.usage)
        if response.stop_reason == "refusal":
            turn.narration = REFUSAL_NARRATION
            return turn
        calls = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        if response.stop_reason != "tool_use" or not calls:
            reminder = completion(_text_of(response)) if completion is not None else None
            if reminder and reminders < MAX_REMINDERS and not last_round:
                reminders += 1
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": reminder})
                continue
            turn.narration = _text_of(response) or EMPTY_NARRATION
            return turn
        # Send the whole assistant turn back, thinking blocks included.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in calls:
            result, is_error = dispatch(call.name, call.input)
            turn.tool_calls.append(ToolCall(call.name, call.input, result, is_error))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False, sort_keys=True),
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": results})
    turn.narration = turn.narration or EMPTY_NARRATION
    return turn


def summarize(
    client: ModelClient,
    config: DMConfig,
    call: CallType,
    request: str,
    on_usage: UsageHook | None = None,
    guard: Guard | None = None,
    *,
    system: str = SUMMARY_SYSTEM,
    max_tokens: int | None = None,
) -> str:
    """One no-tools call on the cheap model: beat summaries, folds, recaps, stories."""
    model = config.model_for(call)
    if guard is not None:
        guard()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens or config.summary_max_tokens,
        system=system,
        messages=[{"role": "user", "content": request}],
    )
    if on_usage is not None:
        on_usage(call, model, response.usage)
    if response.stop_reason == "refusal":
        return ""
    return _text_of(response)
