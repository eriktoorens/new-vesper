"""Tool handlers: every DM request is validated here before any state is written.

Each handler takes the raw tool input (untrusted: it may carry anything a
player managed to talk the model into) and either returns a result for the
model or raises ToolError. A handler runs inside one transaction, so a
rejected request never partially applies.
"""

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from new_vesper.budget.policy import stamp
from new_vesper.city import npcs as npc_places
from new_vesper.city.encounters import NoSuchEncounter, spend
from new_vesper.city.moods import mood_now
from new_vesper.city.npcs import Whereabouts, present_at, regulars_elsewhere, where_is
from new_vesper.city.sky import describe_sky, harder, minimum_rung
from new_vesper.content.loader import Content
from new_vesper.content.loot import roll_loot
from new_vesper.dm import needs as bodily
from new_vesper.dm.speech import SpeechError, check_gist_roll
from new_vesper.rules.attitudes import Attitude, parse_axis
from new_vesper.rules.character import Sheet, apply_track
from new_vesper.rules.clock import city_day, day_start_utc
from new_vesper.rules.consequences import (
    ConsequenceType,
    allowed,
    validate_consequence,
)
from new_vesper.rules.currency import format_glitter
from new_vesper.rules.dice import Rng
from new_vesper.rules.encounters import Kind as EncounterKind
from new_vesper.rules.errors import RulesError, parse_enum
from new_vesper.rules.languages import check_gist_stat
from new_vesper.rules.leveling import can_level_up, xp_to_advance
from new_vesper.rules.light import apply_deed, encroach, parse_deed_size, parse_direction
from new_vesper.rules.magic import casting_difficulty, casting_stat
from new_vesper.rules.needs import roll_stat as needy_roll_stat
from new_vesper.rules.needs import words as need_words
from new_vesper.rules.resolver import Tier, parse_difficulty, resolve
from new_vesper.rules.stats import Stat, parse_stat
from new_vesper.rules.tracks import (
    TRACK_MAX,
    Track,
    fade_status,
    harm_status,
    must_fall_or_endure,
)
from new_vesper.rules.xp import XP_PER_TRIGGER, parse_trigger
from new_vesper.state import (
    characters,
    clocks,
    favors,
    held_facts,
    items,
    npc_journal,
    npc_minds,
    rolls,
    scenes,
    world,
)
from new_vesper.state.attitudes import (
    TargetKind,
    change_attitude,
    get_attitude,
    memory_of,
    recent_changes,
)
from new_vesper.state.characters import Character
from new_vesper.state.db import atomic
from new_vesper.state.errors import NotFoundError, StateError
from new_vesper.state.events import Actor, Cause, append_event, list_events

MAX_STAKES = 300
MAX_NOTE = 300
MAX_EVIDENCE = 300
MAX_REASON = 300
# Knacks with these tags need hands; a `no-hands` origin cannot use them (D7).
NEEDS_HANDS = "needs-hands"
NO_HANDS = "no-hands"
TECH_MAGIC = "tech-magic"
MAGIC = "magic"
TREATMENT = "treatment"
HALF_FADED = "half-faded"
# A language knack helps only to follow a language you don't speak (D79).
LANGUAGE = "language"
SUCCESS_TIERS = frozenset({Tier.CLEAN, Tier.COST})
# What a gist roll's tier means, for the DM (D78). Code applies it to every say tag.
GIST_OUTCOMES = {
    Tier.CLEAN: "the gist and the tone, for the rest of this scene",
    Tier.COST: (
        "the tone only if you apply narrative_cost; the gist too if you apply a real cost "
        "(harm, fade, take_something, dark_encroaches); for the rest of this scene"
    ),
    Tier.CITY_MOVES: "nothing: it stays gibberish; your move may be that the speaker notices",
}
TIER_WORDS = {
    Tier.CLEAN: "a clean success",
    Tier.COST: "success at a cost",
    Tier.CITY_MOVES: "the city moves",
}
# Consequences that only record what happened; they change no numbers.
NARRATIVE_ONLY = frozenset(
    {
        ConsequenceType.SEPARATE_THEM,
        ConsequenceType.REVEAL_UNWELCOME_TRUTH,
        ConsequenceType.FACTION_TAKES_NOTICE,
        ConsequenceType.NARRATIVE_COST,
        ConsequenceType.SIDE_EFFECT,
    }
)


# How a consequence that changes no numbers reads in the player's bracketed line (D108).
NARRATIVE_WORDS = {
    ConsequenceType.SEPARATE_THEM: "separated",
    ConsequenceType.REVEAL_UNWELCOME_TRUTH: "an unwelcome truth",
    ConsequenceType.FACTION_TAKES_NOTICE: "a faction takes notice",
    ConsequenceType.NARRATIVE_COST: "a price paid in the story",
    ConsequenceType.SIDE_EFFECT: "a side effect",
}


class ToolError(Exception):
    """A request the rules refuse. The message goes back to the model."""


@dataclass
class TurnContext:
    """Everything a handler may touch during one turn."""

    conn: sqlite3.Connection
    content: Content
    rng: Rng
    character_id: int
    player_id: int
    scene_id: int
    now: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Set by handlers so the play loop can react after the turn.
    fall_or_endure_pending: bool = False
    slipped: bool = False
    changes: list[str] = field(default_factory=list)
    roll_ids: list[int] = field(default_factory=list)
    encounters: int = 0  # created this turn
    moved_on: list[str] = field(default_factory=list)  # NPCs who left this turn (D112)
    spoken: str | None = None  # the language the character spoke aloud this turn (D115)

    @property
    def cause(self) -> Cause:
        return Cause(Actor.DM, self.player_id, self.scene_id)


Handler = Callable[[TurnContext, dict[str, Any]], dict[str, Any]]


# --- input checks ----------------------------------------------------------


def _args(raw: object, required: set[str], optional: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ToolError("tool input must be an object")
    missing = required - raw.keys()
    unknown = raw.keys() - required - optional
    if missing:
        raise ToolError(f"missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ToolError(f"unknown fields: {', '.join(sorted(str(k)[:40] for k in unknown))}")
    return raw


def _text(value: object, name: str, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{name} must be non-empty text")
    if len(value) > max_length:
        raise ToolError(f"{name} must be at most {max_length} characters")
    return value.strip()


def _flag(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ToolError(f"{name} must be true or false")
    return value


def _roll_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ToolError("roll_id must be the positive integer call_for_roll returned")
    return value


# --- shared state helpers --------------------------------------------------


def _me(ctx: TurnContext) -> Character:
    return characters.get_character(ctx.conn, ctx.character_id)


def _region_id(ctx: TurnContext) -> str:
    return scenes.get_scene(ctx.conn, ctx.scene_id).region_id


def _is_me(ctx: TurnContext, target: object) -> bool:
    return target == "me" or target == str(ctx.character_id) or target == ctx.character_id


def _require_able(character: Character) -> None:
    if character.sheet.fallen:
        raise ToolError("this character has fallen; nothing more can happen to them")
    if must_fall_or_endure(character.sheet.harm):
        raise ToolError(
            "Fall or Endure is pending: the player must choose before anything else "
            "happens to this character. Narrate the moment and stop."
        )


def _write_sheet(
    ctx: TurnContext, before: Character, after: Sheet, reason: str, cause: Cause | None = None
) -> Character:
    return characters.update_sheet(
        ctx.conn, before.id, before.sheet, after, cause or ctx.cause, reason
    )


def _change_track(
    ctx: TurnContext, track: Track, boxes: int, reason: str, cause: Cause | None = None
) -> dict[str, Any]:
    """Apply Harm or Fade to the acting character, handling full tracks."""
    me = _me(ctx)
    sheet, change = apply_track(me.sheet, track, boxes)
    me = _write_sheet(ctx, me, sheet, reason, cause)
    result: dict[str, Any] = {track.value: change.after}
    if track is Track.HARM:
        result["status"] = harm_status(change.after).value
        if change.filled:
            ctx.fall_or_endure_pending = True
            result["fall_or_endure_pending"] = True
    else:
        result["status"] = fade_status(change.after).value
        if change.filled:
            result["slipped_into_old_vesper"] = _slip(ctx, me, cause)
    ctx.changes.append(f"{track.value} {change.before} -> {change.after}")
    return result


def _slip(ctx: TurnContext, me: Character, cause: Cause | None = None) -> str | None:
    """Full Fade in the prototype (D15): move to the Underside entrance, gain half-faded."""
    ctx.slipped = True
    characters.add_character_tag(ctx.conn, me.id, HALF_FADED, cause or ctx.cause)
    entrance = ctx.content.underside_entrance(_region_id(ctx))
    if entrance is None:
        return None
    characters.move_character(ctx.conn, me.id, entrance.id, cause or ctx.cause)
    return entrance.id


def _events_this_scene(ctx: TurnContext, kind: str) -> list[Any]:
    return list_events(ctx.conn, scene_id=ctx.scene_id, kind=kind, limit=10_000)


# --- look ------------------------------------------------------------------


def roll_stat(ctx: TurnContext, character: Character, stat: Stat) -> int:
    """The stat a roll uses: after Harm, then the character's needs (D84)."""
    levels = bodily.levels(ctx.conn, ctx.content, character)
    return needy_roll_stat(character.sheet.roll_stat(stat), stat, levels)


def describe_character(ctx: TurnContext, character: Character) -> dict[str, Any]:
    sheet = character.sheet
    knacks = []
    for knack_id in (*sheet.knacks, *sheet.advanced_knacks):
        knack = world.get_knack(ctx.conn, knack_id)
        knacks.append(
            {"id": knack.id, "name": knack.name, "stat": knack.stat.value, "limits": knack.limits}
        )
    return {
        "id": character.id,
        "name": character.name,
        "pronouns": character.pronouns,
        "age": character.age,
        "appearance": character.appearance,
        "languages": [
            ctx.content.languages[lang].name
            for lang in character.languages
            if lang in ctx.content.languages
        ],
        "origin": character.origin_id,
        "tags": sorted(character.tags),
        "bond": character.bond,
        "level": sheet.level,
        "xp": sheet.xp,
        "xp_to_next_level": xp_to_advance(sheet.level),
        "can_level_up": can_level_up(sheet),
        "harm": {"boxes": sheet.harm, "of": TRACK_MAX, "status": harm_status(sheet.harm).value},
        "fade": {"boxes": sheet.fade, "of": TRACK_MAX, "status": fade_status(sheet.fade).value},
        "stats": {s.value: sheet.stats[s] for s in Stat},
        "roll_stats": {s.value: roll_stat(ctx, character, s) for s in Stat},
        "needs": bodily.describe(bodily.levels(ctx.conn, ctx.content, character)),
        "knacks": knacks,
        "scars": list(sheet.scars),
        "currency": format_glitter(character.currency),
        "items": [{"id": i.id, "name": i.name} for i in items.items_held(ctx.conn, character.id)],
        "favors_owed": [
            {"god": f.god_id, "reason": f.reason}
            for f in favors.favors_owed(ctx.conn, character.id)
        ],
        "location": character.location_id,
        "speaking_aloud": ctx.content.languages[character.speaking].name
        if character.speaking in ctx.content.languages
        else character.speaking,
        "fallen": sheet.fallen,
        "slipped": sheet.slipped,
        "fall_or_endure_pending": must_fall_or_endure(sheet.harm) and not sheet.fallen,
    }


def personality(npc: Any) -> dict[str, Any]:
    return {"traits": list(npc.traits), "speech": list(npc.speech), "sample_line": npc.sample_line}


def _default_feeling(
    ctx: TurnContext, npc: Any, kind: TargetKind, target: str | int
) -> tuple[Attitude, str | None]:
    if kind is TargetKind.CHARACTER:
        s = npc.attitude_to_strangers
        return Attitude(s.trust, s.fondness, s.fear), None
    authored = npc.attitudes.get(target)
    if authored is None:
        return Attitude(), None
    return Attitude(authored.trust, authored.fondness, authored.fear), authored.why


def feelings(ctx: TurnContext, npc: Any, kind: TargetKind, target: str | int) -> dict[str, Any]:
    """How the NPC feels, in numbers and words, and why: the reasons behind recent changes."""
    default, authored_why = _default_feeling(ctx, npc, kind, target)
    now = get_attitude(ctx.conn, npc.id, kind, target, default)
    changes = recent_changes(ctx.conn, npc.id, kind, target, limit=3)
    why = [f"{c.axis.value} {c.before:+d}->{c.after:+d}: {c.reason}" for c in changes]
    if authored_why:
        why.append(f"long-standing: {authored_why}")
    return {
        "trust": now.trust,
        "fondness": now.fondness,
        "fear": now.fear,
        "in_words": now.words(),
        "why": why,
    }


def remembered(ctx: TurnContext, npc: Any) -> dict[str, Any] | None:
    memory = memory_of(ctx.conn, npc.id, ctx.character_id)
    if memory.summary is None and not memory.notes:
        return None
    return {"long_ago": memory.summary, "recently": list(memory.notes)}


def _npc_relations(ctx: TurnContext, npc_id: str) -> list[str]:
    rows = ctx.conn.execute(
        "SELECT target_id FROM attitudes WHERE holder_npc = ? AND target_kind = 'npc'"
        " ORDER BY target_id",
        (npc_id,),
    )
    return [r[0] for r in rows if r[0] in ctx.content.npcs]


def npc_lately(conn: sqlite3.Connection, npc: Any) -> str | None:
    """The latest step of an NPC's own goal, advanced by the daily tick."""
    row = conn.execute("SELECT stage FROM npc_goals WHERE npc_id = ?", (npc.id,)).fetchone()
    if row is None or row[0] == 0:
        return None
    return npc.goal.stages[min(row[0], len(npc.goal.stages)) - 1]


def _languages_here(ctx: TurnContext, location_id: str) -> dict[str, str]:
    """How widely each language is spoken here: the district's, sharpened by the place's."""
    place = ctx.content.locations[location_id]
    spread = dict(ctx.content.regions[place.region_id].languages) | dict(place.languages)
    return {ctx.content.languages[lang].name: level.value for lang, level in spread.items()}


def _clock_time(minutes: int) -> str:
    """'5:00 pm' from minutes after city midnight."""
    hour, minute = divmod(minutes, 60)
    return f"{(hour - 1) % 12 + 1}:{minute:02d} {'am' if hour < 12 else 'pm'}"


def _agenda(ctx: TurnContext, w: Whereabouts) -> dict[str, Any]:
    """What an NPC's day calls for now, when it isn't what they're doing (D112)."""
    plan = w.agenda
    return {
        "where": ctx.content.locations[plan.location].name if plan.location else "away",
        "doing": plan.activity,
        "since": _clock_time(plan.starts),
    }


def journal(ctx: TurnContext, npc: Any) -> dict[str, Any]:
    """Everything the Narrator needs to play an NPC truly, in one place (D125).

    at_heart is authored; wants_now and their tensions are kept by code and change only
    at scene close (D124, D126); lately, memories and knowledge are as before.
    """
    wants = npc_journal.active_wants(ctx.conn, npc.id)
    mine = {w.id for w in wants}
    everyone = {w.id: w for w in npc_journal.active_wants(ctx.conn)}

    def said(want_id: int) -> str:
        w = everyone[want_id]
        whose = "" if w.npc_id == npc.id else f"{ctx.content.npcs[w.npc_id].name}: "
        return f"{whose}{w.want}"

    return {
        "at_heart": npc.wants,
        "wants_now": [
            {"id": w.id, "want": w.want, "about": w.about, "why": w.reason} for w in wants
        ],
        "tensions": [
            {"between": [said(t.want_a), said(t.want_b)], "how": t.note}
            for t in npc_journal.tensions_with(ctx.conn, mine)
        ],
        "lately": npc_lately(ctx.conn, npc),
        "remembers_about_you": remembered(ctx, npc),
        # What they know about the character, and nothing else (D121).
        "knows_about_you": _known(ctx, npc.id),
    }


def _known(ctx: TurnContext, npc_id: str) -> dict[str, Any]:
    found = held_facts.known(ctx.conn, npc_id, ctx.character_id)
    return {"long_ago": found.summary, "facts": list(found.facts)}


def _npcs_here(ctx: TurnContext, me: Character) -> set[str]:
    """NPCs where the character is, and any who moved on this turn (still in its telling)."""
    here = {w.npc.id for w in present_at(ctx.conn, ctx.content, me.location_id or "", ctx.now)}
    return here | set(ctx.moved_on)


def identity(ctx: TurnContext, me: Character) -> dict[str, Any]:
    """Who and what is here, short, every turn: facts narration must not contradict (D117)."""
    origin = ctx.content.origins.get(me.origin_id)
    others: list[dict[str, Any]] = [
        {
            "name": w.npc.name,
            "is": w.npc.role,
            "pronouns": w.npc.pronouns,
            "looks": w.npc.appearance,
        }
        for w in present_at(ctx.conn, ctx.content, me.location_id or "", ctx.now)
    ]
    for (raw,) in ctx.conn.execute(
        "SELECT stranger FROM encounters WHERE scene_id = ? AND stranger IS NOT NULL ORDER BY id",
        (ctx.scene_id,),
    ):
        stranger = json.loads(raw)
        others.append(
            {"name": stranger["name"], "is": stranger["role"], "pronouns": stranger["pronouns"]}
        )
    lying = ctx.conn.execute(
        "SELECT name FROM items WHERE location_id = ? AND destroyed = 0 ORDER BY id",
        (me.location_id,),
    ).fetchall()
    return {
        "player_character": {
            "name": me.name,
            "is": origin.name if origin else me.origin_id,
            "pronouns": me.pronouns,
            "body": me.body,
            "looks": me.appearance,
        },
        "others_here": others,
        "items_held": [i.name for i in items.items_held(ctx.conn, me.id)],
        "items_here": [row[0] for row in lying],
    }


def describe_location(ctx: TurnContext, location_id: str) -> dict[str, Any]:
    place = ctx.content.locations[location_id]
    region = world.get_region(ctx.conn, place.region_id)
    god = ctx.content.shrine_god(place.id)
    present = present_at(ctx.conn, ctx.content, place.id, ctx.now)
    speaking = _me(ctx).speaking
    lying = ctx.conn.execute(
        "SELECT id, name FROM items WHERE location_id = ? AND destroyed = 0 ORDER BY id",
        (place.id,),
    ).fetchall()
    return {
        "id": place.id,
        "name": place.name,
        "region": region.id,
        "region_light": region.light,
        "is_haven": place.is_haven,
        "tags": sorted(place.tags),
        "description": place.description,
        "languages_heard_here": _languages_here(ctx, place.id),
        "npcs": [
            {
                "id": w.npc.id,
                "name": w.npc.name,
                "pronouns": w.npc.pronouns,
                "age": w.npc.age,
                "appearance": w.npc.appearance,
                "role": w.npc.role,
                "languages": [ctx.content.languages[lang].name for lang in w.npc.languages],
                # Whether they understand what the character speaks aloud (D80).
                "understands_you": speaking in w.npc.languages,
                "doing": w.activity,
                # Only when their day calls them elsewhere or to something else (D112).
                **({} if w.on_agenda else {"agenda": _agenda(ctx, w)}),
                # Today's mood, rolled by code (D119).
                "mood": mood_now(ctx.conn, ctx.content, w.npc, ctx.now).mood,
                "personality": personality(w.npc),
                "feels_about_you": feelings(ctx, w.npc, TargetKind.CHARACTER, ctx.character_id),
                # One picture of them: wants, tensions, goal, memories and knowledge (D125).
                "journal": journal(ctx, w.npc),
                "feels_about_others_here": {
                    other.npc.name: feelings(ctx, w.npc, TargetKind.NPC, other.npc.id)
                    for other in present
                    if other.npc.id != w.npc.id
                },
            }
            for w in present
        ],
        # Only for hints, and only if someone present would plausibly know (D53).
        "regulars_elsewhere": [
            {
                "name": w.npc.name,
                "where": ctx.content.locations[w.location].name if w.location else "away",
                "doing": w.activity,
            }
            for w in regulars_elsewhere(ctx.conn, ctx.content, place.id, ctx.now)
        ],
        "shrine_of": god.id if god else None,
        "sky": describe_sky(ctx.content, place.id, ctx.now),
        "items_here": [{"id": row[0], "name": row[1]} for row in lying],
    }


def look(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"entity"})
    entity = args["entity"]
    if not isinstance(entity, str) or not entity.strip():
        raise ToolError("entity must be an id, 'me' or 'here'")
    entity = entity.strip()
    content = ctx.content
    if entity == "me":
        return {"character": describe_character(ctx, _me(ctx))}
    if entity == "here":
        location = _me(ctx).location_id
        if location is None:
            raise ToolError("this character is not anywhere")
        return {"location": describe_location(ctx, location)}
    if entity in content.locations:
        return {"location": describe_location(ctx, entity)}
    if entity in content.regions:
        region = world.get_region(ctx.conn, entity)
        return {
            "region": {
                "id": region.id,
                "name": region.name,
                "light": region.light,
                "fallen": region.fallen,
                "description": content.regions[entity].description,
                "locations": [loc.id for loc in content.locations_in(entity)],
                "threat_clocks": [
                    {"id": c.id, "name": c.name, "filled": c.filled, "segments": c.segments}
                    for c in clocks.clocks_in(ctx.conn, entity)
                ],
            }
        }
    if entity in content.npcs:
        npc = content.npcs[entity]
        now_at = where_is(ctx.conn, content, npc.id, ctx.now)
        return {
            "npc": {
                "id": npc.id,
                "name": npc.name,
                "pronouns": npc.pronouns,
                "home": npc.location,
                "right_now": {
                    "where": now_at.location or "away",
                    "doing": now_at.activity,
                },
                "role": npc.role,
                "description": npc.description,
                "goal": npc.goal.text,
                "personality": personality(npc),
                "feels_about_you": feelings(ctx, npc, TargetKind.CHARACTER, ctx.character_id),
                "journal": journal(ctx, npc),
                "feels_about_others": {
                    ctx.content.npcs[other].name: feelings(ctx, npc, TargetKind.NPC, other)
                    for other in _npc_relations(ctx, npc.id)
                },
                "voice": npc.voice,
            }
        }
    if entity in content.gods:
        god = content.gods[entity]
        owed = [f for f in favors.favors_owed(ctx.conn, ctx.character_id) if f.god_id == god.id]
        return {
            "god": {
                "id": god.id,
                "name": god.name,
                "kind": god.kind.value,
                "shrine": god.shrine,
                "domain": god.domain,
                "description": god.description,
                "wants": god.wants,
                "grievance": god.grievance,
                "ways_to_collect": list(god.collects),
                "favors_this_character_owes": len(owed),
            }
        }
    if entity in content.clocks:
        clock = clocks.get_clock(ctx.conn, entity)
        return {
            "threat_clock": {
                "id": clock.id,
                "name": clock.name,
                "filled": clock.filled,
                "segments": clock.segments,
                "full": clock.full,
                "description": content.clocks[entity].description,
            }
        }
    if entity in content.knacks:
        knack = content.knacks[entity]
        return {
            "knack": {
                "id": knack.id,
                "name": knack.name,
                "stat": knack.stat.value,
                "trigger": knack.trigger,
                "on_10_plus": knack.clean_effect,
                "on_7_to_9": knack.cost_effect,
                "roll_bonus": knack.roll_bonus,
                "limit": knack.limit.describe() if knack.limit else None,
                "tags": sorted(knack.tags),
            }
        }
    raise ToolError(
        f"unknown entity {entity[:40]!r}; use 'me', 'here', or an id of a location, "
        "region, npc, god, threat clock or knack"
    )


# --- call_for_roll ---------------------------------------------------------


def _check_knack(ctx: TurnContext, me: Character, knack_id: object, stat: Stat) -> Any:
    if not isinstance(knack_id, str):
        raise ToolError("knack must be a knack id")
    if knack_id not in (*me.sheet.knacks, *me.sheet.advanced_knacks):
        raise ToolError(f"this character does not have the knack {knack_id[:40]!r}")
    knack = ctx.content.knacks.get(knack_id)
    if knack is None:
        raise ToolError(f"knack {knack_id!r} is not in the catalog")
    if NEEDS_HANDS in knack.tags and NO_HANDS in me.tags:
        raise ToolError(f"{knack.name} needs hands, and this character has none")
    tech = TECH_MAGIC in knack.tags
    if knack.stat is not stat and not (tech and stat is Stat.WIRE):
        raise ToolError(f"{knack.name} rolls {knack.stat.value}, not {stat.value}")
    if knack.limit is not None:
        if knack.limit.per.value == "scene":
            used = rolls.knack_uses(ctx.conn, me.id, knack.id, scene_id=ctx.scene_id)
        else:
            # The city's day turns over at city midnight (D50).
            midnight = stamp(day_start_utc(ctx.now))
            used = rolls.knack_uses(ctx.conn, me.id, knack.id, since=midnight)
        if used >= knack.limit.uses:
            raise ToolError(f"{knack.name} is used up: {knack.limit.describe()}")
    return knack


def call_for_roll(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"stat", "difficulty", "stakes"}, {"knack", "magic", "language"})
    try:
        stat = parse_stat(args["stat"])
        difficulty = parse_difficulty(args["difficulty"])
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    stakes = _text(args["stakes"], "stakes", MAX_STAKES)
    magic = _flag(args.get("magic", False), "magic")
    me = _me(ctx)
    _require_able(me)
    if ctx.roll_ids:
        # One action, one roll (D98): the dice have spoken, and the DM cannot fish again.
        raise ToolError(
            f"this action already has its roll (roll_id {ctx.roll_ids[0]}), and its result "
            "stands: do not roll again this turn. Apply that roll's consequence if it owes "
            "one, and narrate what it decided."
        )
    knack = None
    if "knack" in args and args["knack"] is not None:
        knack = _check_knack(ctx, me, args["knack"], stat)
        magic = magic or MAGIC in knack.tags
    language = None
    if args.get("language") is not None:
        # A gist roll: following speech in a language the character doesn't speak (D78).
        if magic:
            raise ToolError("following a language is not a casting; don't set magic")
        try:
            check_gist_stat(stat)
            language = check_gist_roll(
                ctx, me, args["language"], None if knack is None else LANGUAGE in knack.tags
            )
        except (RulesError, SpeechError) as exc:
            raise ToolError(str(exc)) from exc
    elif knack is not None and LANGUAGE in knack.tags:
        raise ToolError(f"{knack.name} is for following a language: name it in language")
    notes = []
    if magic:
        tech = knack is not None and TECH_MAGIC in knack.tags
        try:
            casting_stat(stat, tech_magic=tech)
        except RulesError as exc:
            raise ToolError(str(exc)) from exc
        forced = casting_difficulty(knack is not None, difficulty)
        if forced is not difficulty:
            notes.append("raw magic without a knack is always Desperate")
        difficulty = forced
    if me.location_id is not None:
        # The tide can make a place harder than the DM's rung, never easier (D59).
        imposed = minimum_rung(ctx.content.locations[me.location_id].tide, stat, ctx.now)
        if imposed is not None and harder(imposed[0], difficulty) is not difficulty:
            notes.append(f"the tide makes this {imposed[0].value}: {imposed[1]}")
            difficulty = imposed[0]
    bonus = knack.roll_bonus if knack else 0
    result = resolve(roll_stat(ctx, me, stat), difficulty, ctx.rng, bonus)
    with atomic(ctx.conn):
        roll = rolls.record_roll(
            ctx.conn,
            me.id,
            ctx.scene_id,
            stat,
            difficulty,
            result,
            stakes,
            ctx.cause,
            knack_id=knack.id if knack else None,
            magic=magic,
            language_id=language,
        )
        outcome: dict[str, Any] = {
            "roll_id": roll.id,
            "dice": list(result.dice),
            "stat": stat.value,
            "stat_value": result.stat_value,
            "difficulty": difficulty.value,
            "modifier": result.modifier,
            "knack_bonus": result.bonus,
            "total": result.total,
            "tier": result.tier.value,
            "magic": magic,
            "allowed_consequences": {k.value: v for k, v in allowed(result.tier, magic).items()},
        }
        if language is not None:
            outcome["following"] = ctx.content.languages[language].name
            outcome["understanding"] = GIST_OUTCOMES[result.tier]
        treated = knack is not None and TREATMENT in knack.tags
        if treated and result.tier in SUCCESS_TIERS and me.sheet.harm > 0:
            # A treatment knack clears 1 Harm per successful use (D8).
            outcome["treatment"] = _change_track(ctx, Track.HARM, -1, knack.name)
    ctx.changes.append(f"{stat.value.title()} roll: {result.total}, {TIER_WORDS[result.tier]}")
    ctx.roll_ids.append(roll.id)
    if notes:
        outcome["notes"] = notes
    return outcome


# --- apply_consequence -----------------------------------------------------


def _load_roll(ctx: TurnContext, roll_id: int) -> rolls.Roll:
    try:
        roll = rolls.get_roll(ctx.conn, roll_id)
    except NotFoundError as exc:
        raise ToolError(f"no roll {roll_id}") from exc
    if roll.character_id != ctx.character_id or roll.scene_id != ctx.scene_id:
        raise ToolError(f"roll {roll_id} does not belong to this character in this scene")
    return roll


def _known_entity(ctx: TurnContext, target: object) -> str:
    if not isinstance(target, str) or not target.strip():
        raise ToolError("target must be 'me' or an entity id")
    target = target.strip()
    content = ctx.content
    known = (
        target == "me"
        or target in content.locations
        or target in content.regions
        or target in content.npcs
        or target in content.gods
        or target in content.clocks
    )
    if not known:
        raise ToolError(f"unknown target {target[:40]!r}")
    return target


def apply_consequence(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"roll_id", "type", "target", "magnitude"}, {"note"})
    roll = _load_roll(ctx, _roll_id(args["roll_id"]))
    if roll.consequence_used:
        raise ToolError(f"roll {roll.id} already has its consequence")
    try:
        consequence = validate_consequence(roll.tier, roll.magic, args["type"], args["magnitude"])
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    note = _text(args["note"], "note", MAX_NOTE) if args.get("note") is not None else ""
    kind, size, target = consequence.type, consequence.magnitude, args["target"]
    me = _me(ctx)
    if me.sheet.fallen:
        raise ToolError("this character has fallen; nothing more can happen to them")
    result: dict[str, Any] = {"type": kind.value, "magnitude": size}
    with atomic(ctx.conn):
        if kind in (ConsequenceType.DEAL_HARM, ConsequenceType.ADD_FADE):
            if not _is_me(ctx, target):
                raise ToolError(
                    "a roll's consequences land on the character who rolled; "
                    "harming another player's character needs an opposed roll, "
                    "which is not supported yet"
                )
            track = Track.HARM if kind is ConsequenceType.DEAL_HARM else Track.FADE
            result |= _change_track(ctx, track, size, note or kind.value)
        elif kind is ConsequenceType.TAKE_SOMETHING:
            held = {i.id: i for i in items.items_held(ctx.conn, me.id)}
            if isinstance(target, bool) or not isinstance(target, int) or target not in held:
                options = ", ".join(f"{i.id} ({i.name})" for i in held.values()) or "none"
                raise ToolError(
                    f"target must be the id of an item this character holds; holding: {options}"
                )
            items.destroy_item(ctx.conn, target, ctx.cause)
            result["taken"] = held[target].name
            ctx.changes.append(f"lost {held[target].name}")
        elif kind is ConsequenceType.DARK_ENCROACHES:
            region = _region_id(ctx)
            if target != region:
                raise ToolError(f"the dark can only encroach on this scene's region, {region!r}")
            before = world.get_region(ctx.conn, region).light
            if before == 0:
                raise ToolError("this region has already fallen into Old Vesper")
            after = world.apply_light_change(
                ctx.conn,
                region,
                encroach(before),
                ctx.cause,
                note or "the dark encroaches",
                source="consequence",
            )
            result["light"] = after.light
            ctx.changes.append(f"{region} Light {before} -> {after.light}")
        elif kind is ConsequenceType.ADVANCE_THREAT_CLOCK:
            if not isinstance(target, str) or target not in ctx.content.clocks:
                raise ToolError(f"target must be a threat clock id: {sorted(ctx.content.clocks)}")
            clock = clocks.get_clock(ctx.conn, target)
            if clock.region_id != _region_id(ctx):
                raise ToolError("only this region's threat clocks can advance here")
            try:
                clock = clocks.advance_clock(ctx.conn, clock.id, ctx.cause)
            except StateError as exc:
                raise ToolError(str(exc)) from exc
            result |= {
                "clock": clock.id,
                "filled": clock.filled,
                "segments": clock.segments,
                "full": clock.full,
            }
            ctx.changes.append(f"{clock.name} {clock.filled}/{clock.segments}")
        elif kind is ConsequenceType.FAVOR_OWED:
            if not isinstance(target, str) or target not in ctx.content.gods:
                raise ToolError(f"target must be a god id: {sorted(ctx.content.gods)}")
            favor = favors.record_favor(ctx.conn, me.id, target, note or roll.stakes, ctx.cause)
            result["favor_owed_to"] = favor.god_id
            ctx.changes.append(f"owes {favor.god_id} a favor")
        else:
            entity = _known_entity(ctx, target)
            append_event(
                ctx.conn,
                "consequence",
                ctx.cause,
                {"type": kind.value, "target": entity, "note": note, "roll_id": roll.id},
                character_id=me.id,
            )
            result["recorded"] = True
            assert kind in NARRATIVE_ONLY
            # Shown to the player like any other consequence, though no number moves (D108).
            lead = "cost" if roll.tier is Tier.COST else "the city moves"
            ctx.changes.append(f"{lead}: {NARRATIVE_WORDS[kind]}")
        rolls.use_roll(ctx.conn, roll.id, rolls.RollUse.CONSEQUENCE, kind.value)
    return result


# --- grant_from_table ------------------------------------------------------


def grant_from_table(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"roll_id", "table_id"})
    roll = _load_roll(ctx, _roll_id(args["roll_id"]))
    if roll.tier not in SUCCESS_TIERS:
        raise ToolError("loot needs a successful roll (7 or more)")
    if roll.loot_used:
        raise ToolError(f"roll {roll.id} has already granted loot")
    table_id = args["table_id"]
    if not isinstance(table_id, str) or table_id not in ctx.content.loot_tables:
        raise ToolError(f"unknown table; tables: {sorted(ctx.content.loot_tables)}")
    me = _me(ctx)
    _require_able(me)
    entry = roll_loot(ctx.content.loot_tables[table_id], ctx.rng)
    with atomic(ctx.conn):
        item = items.create_item(ctx.conn, entry.kind, entry.name, ctx.cause, character_id=me.id)
        rolls.use_roll(ctx.conn, roll.id, rolls.RollUse.LOOT)
    ctx.changes.append(f"gained {item.name}")
    return {"item_id": item.id, "item": item.name}


# --- report_trigger --------------------------------------------------------


def report_trigger(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"trigger_id", "evidence"})
    try:
        trigger = parse_trigger(args["trigger_id"])
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    evidence = _text(args["evidence"], "evidence", MAX_EVIDENCE)
    me = _me(ctx)
    if me.sheet.fallen:
        raise ToolError("this character has fallen")
    paid = [
        e
        for e in _events_this_scene(ctx, "xp_awarded")
        if e.character_id == me.id and e.payload.get("trigger") == trigger.value
    ]
    if paid:
        return {"paid": False, "reason": f"{trigger.value} already paid out this scene"}
    if trigger.value == "raise_light":
        raised = [
            e
            for e in _events_this_scene(ctx, "light_changed")
            if e.payload.get("source") == "adjust_light"
            and e.payload["after"] > e.payload["before"]
        ]
        if not raised:
            return {"paid": False, "reason": "no Light was raised in this scene"}
    with atomic(ctx.conn):
        me = _write_sheet(
            ctx, me, replace(me.sheet, xp=me.sheet.xp + XP_PER_TRIGGER), f"trigger {trigger.value}"
        )
        append_event(
            ctx.conn,
            "xp_awarded",
            ctx.cause,
            {"trigger": trigger.value, "xp": XP_PER_TRIGGER, "evidence": evidence},
            character_id=me.id,
        )
    ctx.changes.append(f"+{XP_PER_TRIGGER} XP ({trigger.value})")
    return {
        "paid": True,
        "xp": me.sheet.xp,
        "xp_to_next_level": xp_to_advance(me.sheet.level),
        "can_level_up": can_level_up(me.sheet),
    }


# --- adjust_light ----------------------------------------------------------


def adjust_light(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    args = _args(raw, {"region", "direction", "size", "reason"})
    try:
        direction = parse_direction(args["direction"])
        size = parse_deed_size(args["size"])
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    reason = _text(args["reason"], "reason", MAX_REASON)
    region_id = _region_id(ctx)
    if args["region"] != region_id:
        raise ToolError(f"only this scene's region, {region_id!r}, can change here")
    earlier = [
        e
        for e in _events_this_scene(ctx, "light_changed")
        if e.region_id == region_id and e.payload.get("source") == "adjust_light"
    ]
    if earlier:
        raise ToolError("this region's Light has already changed this scene (one per scene)")
    if size.value == "major" and not _events_this_scene(ctx, "xp_awarded"):
        raise ToolError("a major change needs an XP trigger reported in this scene first")
    region = world.get_region(ctx.conn, region_id)
    if region.fallen:
        raise ToolError("this region has fallen into Old Vesper")
    change = apply_deed(region.light, direction, size)
    after = world.apply_light_change(
        ctx.conn, region.id, change, ctx.cause, reason, source="adjust_light"
    )
    ctx.changes.append(f"{region.id} Light {change.before} -> {after.light}")
    return {"region": region.id, "light": after.light, "fell": change.fell}


# --- adjust_attitude ------------------------------------------------------------


def adjust_attitude(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    """An NPC's feelings move one step on one axis, with a reason (D61, D62, D65)."""
    args = _args(raw, {"npc", "toward", "axis", "direction", "reason"})
    try:
        axis = parse_axis(args["axis"])
        direction = parse_direction(args["direction"])
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    reason = _text(args["reason"], "reason", MAX_REASON)
    me = _me(ctx)
    here = _npcs_here(ctx, me)
    npc_id = args["npc"]
    if not isinstance(npc_id, str) or npc_id not in ctx.content.npcs:
        raise ToolError(f"unknown npc; here now: {sorted(here) or 'nobody'}")
    if npc_id not in here:
        raise ToolError(f"{ctx.content.npcs[npc_id].name} is not here")
    toward = args["toward"]
    npc = ctx.content.npcs[npc_id]
    if _is_me(ctx, toward):
        kind, target = TargetKind.CHARACTER, ctx.character_id
        label = me.name
    elif isinstance(toward, str) and toward in ctx.content.npcs:
        if toward == npc_id:
            raise ToolError("an NPC's feelings about themselves are not tracked")
        if toward not in here:
            raise ToolError(f"{ctx.content.npcs[toward].name} is not here")
        kind, target, label = TargetKind.NPC, toward, ctx.content.npcs[toward].name
    else:
        raise ToolError("toward must be 'me' or the id of another NPC who is here")
    default, _ = _default_feeling(ctx, npc, kind, target)
    delta = 1 if direction.value == "raise" else -1
    try:
        after = change_attitude(
            ctx.conn, npc_id, kind, target, axis, delta, reason, ctx.cause, default=default
        )
    except StateError as exc:
        raise ToolError(str(exc)) from exc
    ctx.changes.append(f"{npc.name}'s {axis.value} toward {label}: {after.words()[axis.value]}")
    return {
        "npc": npc_id,
        "toward": label,
        axis.value: after.value(axis),
        "in_words": after.words()[axis.value],
    }


# --- create_encounter ---------------------------------------------------------

MAX_ENCOUNTER_TEXT = 300
MAX_ROLE = 120


def create_encounter(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    """The DM writes an encounter; code spends a slot of that kind from today's pool (D73)."""
    args = _args(raw, {"kind", "what_happens"}, {"stranger_role"})
    try:
        kind = parse_enum(EncounterKind, args["kind"], "encounter kind")
    except RulesError as exc:
        raise ToolError(str(exc)) from exc
    what = _text(args["what_happens"], "what_happens", MAX_ENCOUNTER_TEXT)
    role = args.get("stranger_role")
    if role is not None:
        role = _text(role, "stranger_role", MAX_ROLE)
    if ctx.encounters >= 1:
        raise ToolError("one encounter per turn")
    me = _me(ctx)
    _require_able(me)
    if me.location_id is None:
        raise ToolError("this character is nowhere")
    try:
        underside, stranger = spend(
            ctx.conn, ctx.content, me.id, me.location_id, kind, what, role, ctx.now, ctx.cause
        )
    except NoSuchEncounter as exc:
        raise ToolError(str(exc)) from exc
    ctx.encounters += 1
    result: dict[str, Any] = {"kind": kind.value, "underside": underside}
    if underside:
        result["note"] = "this is Old Vesper bleeding through: make it uncanny"
    if stranger is not None:
        result["stranger"] = stranger.for_dm(ctx.content)
    return result


# --- bodily needs ------------------------------------------------------------------


def apply_needs(ctx: TurnContext) -> None:
    """Count the time since the last turn against the character's needs (D85).

    A need at its worst costs a box of Harm (Fade for tiredness) per step there
    (D84). Nothing is applied to a character who has fallen or must choose Fall
    or Endure; their needs still count.
    """
    me = _me(ctx)
    if me.sheet.fallen:
        return
    cause = Cause(Actor.SYSTEM, ctx.player_id, ctx.scene_id)
    with atomic(ctx.conn):
        result = bodily.tick(ctx.conn, ctx.content, me, ctx.now)
        for need, level in result.worse.items():
            ctx.changes.append(f"{need.value}: {need_words(need, level)}")
        for need, level in result.better.items():
            ctx.changes.append(f"{need.value}: {need_words(need, level)}")
        for track, boxes in result.owed.items():
            me = _me(ctx)
            full = me.sheet.harm if track is Track.HARM else me.sheet.fade
            if boxes and full < TRACK_MAX:
                _change_track(ctx, track, boxes, "bodily needs at their worst", cause)


def npc_moves_on(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    """An NPC who is here moves on to what their day calls for (D112).

    The Narrator decides when and how it reads; code decides where they go.
    """
    args = _args(raw, {"npc", "reason"})
    reason = _text(args["reason"], "reason", MAX_REASON)
    me = _me(ctx)
    here = {w.npc.id: w for w in present_at(ctx.conn, ctx.content, me.location_id or "", ctx.now)}
    npc_id = args["npc"]
    if not isinstance(npc_id, str) or npc_id not in ctx.content.npcs:
        raise ToolError(f"unknown npc; here now: {sorted(here) or 'nobody'}")
    name = ctx.content.npcs[npc_id].name
    if npc_id not in here:
        raise ToolError(f"{name} is not here")
    if here[npc_id].on_agenda:
        raise ToolError(
            f"{name}'s day keeps them here, doing what they're doing; "
            "if they turn away, narrate it without this tool"
        )
    before, after = npc_places.move_on(ctx.conn, ctx.content, npc_id, ctx.now, ctx.cause, reason)
    ctx.moved_on.append(npc_id)
    left = after.location != before.location
    if left:
        # Where they went isn't the character's to see (D53); the Narrator gets it below.
        ctx.changes.append(f"{name} leaves")
    return {
        "npc": npc_id,
        "left": left,
        "now": {
            "where": ctx.content.locations[after.location].name if after.location else "away",
            "doing": after.activity,
        },
    }


MAX_MOOD = 60


def _npc_here(ctx: TurnContext, raw_id: object) -> Any:
    """An NPC id the Narrator gave, checked: real, and where the character is."""
    here = _npcs_here(ctx, _me(ctx)) - set(ctx.moved_on)
    if not isinstance(raw_id, str) or raw_id not in ctx.content.npcs:
        raise ToolError(f"unknown npc; here now: {sorted(here) or 'nobody'}")
    npc = ctx.content.npcs[raw_id]
    if raw_id not in here:
        raise ToolError(f"{npc.name} is not here")
    return npc


def _one_line(value: object, name: str, max_length: int) -> str:
    clean = _text(value, name, max_length)
    if "\n" in clean or "\r" in clean:
        raise ToolError(f"{name} must be one line")
    return clean


def npc_mood(ctx: TurnContext, raw: dict[str, Any]) -> dict[str, Any]:
    """Something on the page shifts an NPC's mood for the rest of the day (D119).

    Once per NPC per scene.
    """
    args = _args(raw, {"npc", "mood", "reason"})
    npc = _npc_here(ctx, args["npc"])
    mood = _one_line(args["mood"], "mood", MAX_MOOD)
    reason = _one_line(args["reason"], "reason", MAX_REASON)
    if npc_minds.shifted_in_scene(ctx.conn, npc.id, ctx.scene_id):
        raise ToolError(f"{npc.name}'s mood has already shifted this scene")
    before = mood_now(ctx.conn, ctx.content, npc, ctx.now)
    npc_minds.add_mood(
        ctx.conn,
        npc.id,
        city_day(ctx.now),
        mood,
        "narrator",
        reason=reason,
        scene_id=ctx.scene_id,
    )
    append_event(
        ctx.conn,
        "npc_mood_shifted",
        ctx.cause,
        {"npc_id": npc.id, "from": before.mood, "to": mood, "reason": reason},
        character_id=ctx.character_id,
    )
    return {"npc": npc.id, "mood": mood, "was": before.mood}


HANDLERS: dict[str, Handler] = {
    "look": look,
    "call_for_roll": call_for_roll,
    "apply_consequence": apply_consequence,
    "grant_from_table": grant_from_table,
    "report_trigger": report_trigger,
    "adjust_light": adjust_light,
    "adjust_attitude": adjust_attitude,
    "create_encounter": create_encounter,
    "npc_moves_on": npc_moves_on,
    "npc_mood": npc_mood,
}


def dispatch(ctx: TurnContext, name: str, raw: object) -> tuple[dict[str, Any], bool]:
    """Run one tool call. Returns (result, is_error); never raises for bad input."""
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"unknown tool {str(name)[:40]!r}"}, True
    flags = (
        ctx.fall_or_endure_pending,
        ctx.slipped,
        len(ctx.changes),
        len(ctx.roll_ids),
        ctx.encounters,
        len(ctx.moved_on),
    )
    try:
        with atomic(ctx.conn):
            return handler(ctx, raw), False  # type: ignore[arg-type]
    except (ToolError, RulesError, StateError) as exc:
        # The transaction rolled back; the turn's flags roll back with it.
        ctx.fall_or_endure_pending, ctx.slipped = flags[0], flags[1]
        del ctx.changes[flags[2] :]
        del ctx.roll_ids[flags[3] :]
        ctx.encounters = flags[4]
        del ctx.moved_on[flags[5] :]
        return {"error": str(exc)}, True


def owed_consequences(ctx: TurnContext) -> list[rolls.Roll]:
    """Rolls made this turn at 7-9 or 6- that have not had their consequence yet."""
    owed = []
    for roll_id in ctx.roll_ids:
        roll = rolls.get_roll(ctx.conn, roll_id)
        if roll.tier is not Tier.CLEAN and not roll.consequence_used:
            owed.append(roll)
    return owed


def owed_reminder(ctx: TurnContext) -> str | None:
    """The message that sends the DM back to apply a consequence it owes (D1)."""
    me = characters.get_character(ctx.conn, ctx.character_id)
    if me.sheet.fallen or must_fall_or_endure(me.sheet.harm):
        return None  # nothing more can happen to them; the turn may end
    owed = owed_consequences(ctx)
    if not owed:
        return None
    lines = [
        f"roll_id {r.id} ({r.tier.value}, stakes: {r.stakes}) allows "
        + ", ".join(f"{k.value} up to {v}" for k, v in allowed(r.tier, r.magic).items())
        for r in owed
    ]
    return (
        "<rules_check>Before you finish: every roll at 7-9 or 6 or less needs exactly one "
        "consequence, applied with apply_consequence. Still owed: "
        + "; ".join(lines)
        + ". Apply it to the roll you already made; do not roll again. Then tell the turn "
        "once, from the start, with the consequence in it: this telling replaces your "
        "earlier one, so the player sees one outcome, not several.</rules_check>"
    )
