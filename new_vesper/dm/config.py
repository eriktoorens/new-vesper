"""Model routing (D20): Sonnet runs turns; Haiku writes summaries and recaps.

Every call type's model is configurable, from code or environment variables.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum


class CallType(StrEnum):
    TURN = "turn"
    BEAT_SUMMARY = "beat_summary"
    SCENE_SUMMARY = "scene_summary"
    RECAP = "recap"
    NPC_MEMORY = "npc_memory"


@dataclass(frozen=True)
class DMConfig:
    turn_model: str = "claude-sonnet-5"
    summary_model: str = "claude-haiku-4-5"
    recap_model: str = "claude-haiku-4-5"
    # Thinking counts against max_tokens on Sonnet 5, so leave room beyond the prose.
    turn_max_tokens: int = 8000
    turn_effort: str | None = "medium"
    summary_max_tokens: int = 400
    # Tool rounds per turn before the model must narrate without tools.
    max_tool_rounds: int = 8
    recent_beats: int = 3

    def model_for(self, call: CallType) -> str:
        if call is CallType.TURN:
            return self.turn_model
        if call is CallType.RECAP:
            return self.recap_model
        return self.summary_model

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "DMConfig":
        """Override models with NEW_VESPER_TURN_MODEL, _SUMMARY_MODEL, _RECAP_MODEL."""
        base = cls()
        return cls(
            turn_model=env.get("NEW_VESPER_TURN_MODEL", base.turn_model),
            summary_model=env.get("NEW_VESPER_SUMMARY_MODEL", base.summary_model),
            recap_model=env.get("NEW_VESPER_RECAP_MODEL", base.recap_model),
        )
