"""Tool definitions sent to the model. Handlers in handlers.py enforce them.

Schemas describe what is accepted, but validation happens in code: a request
that passes the schema can still be refused by the rules.
"""

from typing import Any

from new_vesper.rules.attitudes import Axis
from new_vesper.rules.consequences import ConsequenceType
from new_vesper.rules.encounters import Kind
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
            "always Desperate. To follow speech in a language the character doesn't speak, roll "
            "Heart and name the language: what the tier earns holds for the rest of the scene."
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
                "language": {
                    "type": "string",
                    "description": "Optional: the language a Heart roll tries to follow.",
                },
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
        "name": "npc_moves_on",
        "description": (
            "An NPC who is here moves on to what their day calls for: their agenda in the "
            "location's npcs. Code decides where they go; you decide when, and write the exit "
            "in this turn (a reason, a parting line, colored by how they feel). Weigh the scene "
            "against their errand: they may stay and run late, or cut a conversation short. "
            "Refused if their day keeps them here, doing what they are doing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "npc": {"type": "string"},
                "reason": {"type": "string", "description": "Why now, in one sentence."},
            },
            "required": ["npc", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "npc_wants",
        "description": (
            "What an NPC who is here wants right now, in this scene: drawn from their wants, "
            'goal, lately and mood, and specific to what is happening ("wants the skewer '
            'thief caught"). Set it when an NPC here has wants_now null, then play them '
            "pursuing it. It may change once per scene, when the scene gives them reason."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "npc": {"type": "string"},
                "want": {"type": "string", "description": "One short line."},
                "reason": {"type": "string", "description": "Why, in one sentence."},
            },
            "required": ["npc", "want", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "npc_learns",
        "description": (
            "An NPC who is here hears or sees something about the player character worth "
            "keeping: their name once it is said, what they are, what they want, what they "
            "did. One plain fact per call, as the NPC would put it; up to three per NPC per "
            "turn. NPCs know only what is in their knows_about_you and what happens in front "
            "of them, so record what matters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "npc": {"type": "string"},
                "fact": {"type": "string", "description": "One short line."},
                "how": {"type": "string", "enum": ["heard", "saw"]},
            },
            "required": ["npc", "fact", "how"],
            "additionalProperties": False,
        },
    },
    {
        "name": "npc_mood",
        "description": (
            "Something on the page shifts the mood of an NPC who is here, for the rest of "
            "the day. Their mood comes from code each morning; change it only when what "
            "happens would plainly change it. Once per NPC per scene."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "npc": {"type": "string"},
                "mood": {"type": "string", "description": "A few words, like their mood now."},
                "reason": {"type": "string", "description": "What happened, in one sentence."},
            },
            "required": ["npc", "mood", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_encounter",
        "description": (
            "Something happens to the acting character that nobody planned: you write it, "
            "fresh, fitting the place, hour, weather and tide. Spends one encounter of that "
            "kind from the district's pool for today (see scene_state.encounters); refused if "
            "none is left. At most one per turn. If a person is involved, give their role and "
            "code will supply their name, pronouns and language. Trouble may lead to a roll; "
            "consequences still only come from rolls."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": _enum(Kind)},
                "what_happens": {"type": "string", "description": "One or two sentences."},
                "stranger_role": {
                    "type": "string",
                    "description": "Optional: who the stranger is, e.g. 'a pickpocket'.",
                },
            },
            "required": ["kind", "what_happens"],
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
