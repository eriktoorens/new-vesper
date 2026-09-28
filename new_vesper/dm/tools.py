"""Tool definitions sent to the model. Handlers in handlers.py enforce them.

Schemas describe what is accepted, but validation happens in code: a request
that passes the schema can still be refused by the rules.
"""

from typing import Any

from new_vesper.rules.attitudes import Axis
from new_vesper.rules.consequences import ConsequenceType
from new_vesper.rules.light import DeedSize, Direction
from new_vesper.rules.resolver import Difficulty
from new_vesper.rules.stats import Stat
from new_vesper.rules.xp import Trigger


def _enum(values: object) -> list[str]:
    return [member.value for member in values]  # type: ignore[attr-defined]


TOOLS: list[dict[str, Any]] = [
    {
        "name": "look",
        "description": (
            "Read current state so narration matches the world. entity is 'me' (the acting "
            "character), 'here' (their location), or the id of a location, region, npc, god, "
            "threat clock or knack. Changes nothing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"entity": {"type": "string"}},
            "required": ["entity"],
            "additionalProperties": False,
        },
    },
    {
        "name": "call_for_roll",
        "description": (
            "Roll 2d6 + stat + difficulty modifier for the acting character when failure would be "
            "interesting. Returns the total, the tier (clean 10+, cost 7-9, city_moves 6-), a "
            "single-use roll_id and the consequences that tier allows. Name a knack only if the "
            "character has it and it fits; set magic for a casting. Raw magic without a knack is "
            "always Desperate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "stat": {"type": "string", "enum": _enum(Stat)},
                "difficulty": {"type": "string", "enum": _enum(Difficulty)},
                "stakes": {
                    "type": "string",
                    "description": "One sentence: what is being attempted and what is at risk.",
                },
                "knack": {"type": "string", "description": "Optional knack id."},
                "magic": {"type": "boolean", "description": "True for a casting."},
            },
            "required": ["stat", "difficulty", "stakes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_consequence",
        "description": (
            "Apply the one consequence a roll allows. On 7-9 pick one cost; on 6- pick one move; "
            "on 10+ call nothing. target is 'me' for deal_harm and add_fade, an item id (integer) "
            "for take_something, this scene's region id for dark_encroaches, a threat clock id for "
            "advance_threat_clock, a god id for favor_owed, and 'me' or an entity id otherwise. "
            "Each roll_id takes one consequence."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "roll_id": {"type": "integer"},
                "type": {"type": "string", "enum": _enum(ConsequenceType)},
                "target": {"type": ["string", "integer"]},
                "magnitude": {"type": "integer", "minimum": 1, "maximum": 3},
                "note": {"type": "string", "description": "Short reason, for the record."},
            },
            "required": ["roll_id", "type", "target", "magnitude"],
            "additionalProperties": False,
        },
    },
    {
        "name": "grant_from_table",
        "description": (
            "Give the acting character one item rolled from a loot table, backed by a successful "
            "roll (7+). Code picks the item; never invent items in narration."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "roll_id": {"type": "integer"},
                "table_id": {"type": "string"},
            },
            "required": ["roll_id", "table_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "report_trigger",
        "description": (
            "Report that an advancement trigger happened on the page. Code decides whether it "
            "pays: each trigger pays 1 XP at most once per character per scene, and raise_light "
            "pays only after this scene's Light was raised."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_id": {"type": "string", "enum": _enum(Trigger)},
                "evidence": {"type": "string", "description": "What happened, in one sentence."},
            },
            "required": ["trigger_id", "evidence"],
            "additionalProperties": False,
        },
    },
    {
        "name": "adjust_attitude",
        "description": (
            "Record that an NPC's feelings shifted because of something that happened on the "
            "page. npc is the NPC whose feelings change; toward is 'me' (the acting character) "
            "or another NPC's id; both must be here. axis is trust, fondness or fear, moved one "
            "step up or down, at most once per axis per scene. The reason is kept, so the NPC "
            "can say why later."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "npc": {"type": "string"},
                "toward": {"type": "string"},
                "axis": {"type": "string", "enum": _enum(Axis)},
                "direction": {"type": "string", "enum": _enum(Direction)},
                "reason": {"type": "string", "description": "Why, in one sentence."},
            },
            "required": ["npc", "toward", "axis", "direction", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "adjust_light",
        "description": (
            "Move this scene's region Light because of a character's deed: deed is 1, major is 2. "
            "At most one change per region per scene; a major change needs an XP trigger reported "
            "in this scene first. Use apply_consequence dark_encroaches for a failed roll instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {"type": "string"},
                "direction": {"type": "string", "enum": _enum(Direction)},
                "size": {"type": "string", "enum": _enum(DeedSize)},
                "reason": {"type": "string"},
            },
            "required": ["region", "direction", "size", "reason"],
            "additionalProperties": False,
        },
        # Tools render first, so a breakpoint here caches every tool definition.
        "cache_control": {"type": "ephemeral"},
    },
]

TOOL_NAMES = frozenset(tool["name"] for tool in TOOLS)
