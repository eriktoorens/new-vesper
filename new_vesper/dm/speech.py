"""Speech in the DM's narration (D76-D81): tagged by the DM, rendered by code.

The DM writes every line someone other than the player character speaks as
``<say who="..." lang="..." tone="..." gist="...">the words</say>``. Code checks
each tag (the speaker is here and speaks that language), then shows the player
only what their character understands: the words in a language they speak,
the gist or tone a gist roll earned them in this scene, or nothing.

A tag that fails its checks is never shown: the words could be a translation
the character has no right to. The DM is sent back to fix it first (D76).
"""

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from new_vesper.city.npcs import present_at
from new_vesper.rules.consequences import ConsequenceType
from new_vesper.rules.errors import RulesError
from new_vesper.rules.languages import COMMON_TONGUE, Heard, gibberish, gist_heard, heard
from new_vesper.rules.resolver import Tier
from new_vesper.state import characters, rolls, speech
from new_vesper.state.characters import Character

if TYPE_CHECKING:
    from new_vesper.dm.handlers import TurnContext

SAY = re.compile(r"<say\b([^>]*)>(.*?)</say\s*>", re.DOTALL | re.IGNORECASE)
ATTR = re.compile(r'([a-z]+)\s*=\s*"([^"]*)"', re.IGNORECASE)
# An opening tag left without its closing tag, and whatever follows it in the paragraph.
UNCLOSED = re.compile(r"<say\b.*?(?=\n\s*\n|\Z)", re.DOTALL | re.IGNORECASE)
STRAY_CLOSE = re.compile(r"</say\s*>", re.IGNORECASE)
ATTRIBUTES = frozenset({"who", "lang", "tone", "gist"})
# Lines of recent speech the DM sees each turn.
RECENT_LINES = 6


class SpeechError(ValueError):
    """A language the rules don't know, or can't be followed here."""


@dataclass(frozen=True)
class Tag:
    start: int
    end: int
    attrs: dict[str, str]
    words: str


@dataclass(frozen=True)
class Line:
    """A checked tag: who said it, in what, and what the character made of it."""

    tag: Tag
    speaker: str
    npc_id: str | None
    language: str | None  # None when the tag's language is unknown
    heard: Heard
    problem: str | None  # why the tag can't stand, if it can't


def parse_tags(narration: str) -> list[Tag]:
    tags = []
    for match in SAY.finditer(narration):
        attrs = {k.lower(): v.strip() for k, v in ATTR.findall(match.group(1))}
        tags.append(Tag(match.start(), match.end(), attrs, match.group(2).strip()))
    return tags


def resolve_language(ctx: "TurnContext", value: object) -> str:
    """A language id from its id or name, any case."""
    if isinstance(value, str):
        key = value.strip().casefold()
        for lang in ctx.content.languages.values():
            if key in (lang.id, lang.name.casefold()):
                return lang.id
    known = ", ".join(sorted(ctx.content.languages))
    raise SpeechError(f"unknown language {str(value)[:40]!r}; languages: {known}")


def strangers_here(ctx: "TurnContext") -> dict[str, frozenset[str]]:
    """Strangers code made for encounters in this scene, and what they speak (D70)."""
    rows = ctx.conn.execute(
        "SELECT stranger FROM encounters WHERE scene_id = ? AND stranger IS NOT NULL",
        (ctx.scene_id,),
    )
    found = {}
    for (raw,) in rows:
        stranger = json.loads(raw)
        found[stranger["name"].casefold()] = frozenset({stranger["language"], COMMON_TONGUE})
    return found


def earned(ctx: "TurnContext") -> dict[str, Heard]:
    """What this scene's gist rolls earned the character, by language (D78)."""
    return {
        roll.language_id: gist_heard(roll.tier, _paid(roll))
        for roll in rolls.gist_rolls(ctx.conn, ctx.character_id, ctx.scene_id)
        if roll.language_id is not None
    }


def _paid(roll: rolls.Roll) -> ConsequenceType | None:
    if roll.tier is not Tier.COST or roll.consequence_type is None:
        return None
    return ConsequenceType(roll.consequence_type)


def heard_here(ctx: "TurnContext", me: Character) -> frozenset[str]:
    """Languages someone here speaks: the people present, the neighborhood, this scene."""
    found: set[str] = set()
    if me.location_id is not None:
        place = ctx.content.locations[me.location_id]
        found |= set(ctx.content.regions[place.region_id].languages) | set(place.languages)
        for w in present_at(ctx.content, place.id, ctx.now):
            found |= set(w.npc.languages)
    for langs in strangers_here(ctx).values():
        found |= langs
    for line in speech.lines_in_scene(ctx.conn, ctx.scene_id, ctx.character_id):
        if line.language_id is not None:
            found.add(line.language_id)
    return frozenset(found)


def check_gist_roll(
    ctx: "TurnContext", me: Character, value: object, knack_is_language: bool | None
) -> str:
    """The language a gist roll tries to follow, if the rules allow the roll (D78, D79).

    ``knack_is_language`` is None with no knack, else whether it is a language knack.
    """
    lang = resolve_language(ctx, value)
    name = ctx.content.languages[lang].name
    if knack_is_language is False:
        raise SpeechError("only a language knack helps follow a language")
    if lang in me.speaks:
        raise SpeechError(f"{me.name} speaks {name}: no roll is needed to understand it")
    if lang not in heard_here(ctx, me):
        raise SpeechError(f"nobody here is speaking {name}")
    if lang in earned(ctx):
        raise SpeechError(
            f"{me.name} has already tried to follow {name} this scene; what they caught stands"
        )
    return lang


def _check(
    ctx: "TurnContext",
    tag: Tag,
    me: Character,
    present: dict[str, Any],
    strangers: dict[str, frozenset[str]],
    gains: dict[str, Heard],
) -> Line:
    who = tag.attrs.get("who", "")

    def bad(problem: str, speaker: str = who or "someone", npc: str | None = None) -> Line:
        return Line(tag, speaker[:80], npc, None, Heard.NONE, problem)

    unknown = set(tag.attrs) - ATTRIBUTES
    if unknown:
        return bad(f"unknown attributes {sorted(unknown)}; use who, lang, tone and gist")
    if not who:
        return bad("give who: an NPC id, a stranger's name, or a short description")
    key = who.casefold()
    if key in ("me", str(me.id), me.name.casefold()):
        return bad(
            f"{me.name}'s own words are the player's: never tag, rewrite or add to them",
            me.name,
        )
    npc = ctx.content.npcs.get(who) or next(
        (n for n in ctx.content.npcs.values() if n.name.casefold() == key), None
    )
    if npc is not None and npc.id not in present:
        return bad(f"{npc.name} is not here", npc.name, npc.id)
    if not tag.words:
        return bad("a say tag needs the words inside it")
    if len(tag.words) > speech.MAX_WORDS:
        return bad(f"keep each line under {speech.MAX_WORDS} characters; split it")
    if len(tag.attrs.get("who", "")) > speech.MAX_SPEAKER:
        return bad(f"keep who under {speech.MAX_SPEAKER} characters")
    if len(tag.attrs.get("tone", "")) > speech.MAX_TONE:
        return bad(f"keep tone under {speech.MAX_TONE} characters")
    if len(tag.attrs.get("gist", "")) > speech.MAX_GIST:
        return bad(f"keep gist under {speech.MAX_GIST} characters")
    speaker = npc.name if npc is not None else who
    try:
        lang = resolve_language(ctx, tag.attrs.get("lang"))
    except SpeechError as exc:
        return bad(f"lang: {exc}", speaker, npc.id if npc else None)
    if npc is not None and lang not in npc.languages and lang != COMMON_TONGUE:
        return bad(f"{npc.name} doesn't speak {ctx.content.languages[lang].name}", speaker, npc.id)
    stranger = strangers.get(key)
    if stranger is not None and lang not in stranger:
        return bad(f"{who} doesn't speak {ctx.content.languages[lang].name}", speaker)
    return Line(tag, speaker, npc.id if npc else None, lang, heard(lang, me.speaks, gains), None)


def check_speech(ctx: "TurnContext", narration: str) -> list[Line]:
    me = characters.get_character(ctx.conn, ctx.character_id)
    present = {w.npc.id: w.npc for w in present_at(ctx.content, me.location_id or "", ctx.now)}
    strangers, gains = strangers_here(ctx), earned(ctx)
    return [_check(ctx, tag, me, present, strangers, gains) for tag in parse_tags(narration)]


def speech_reminder(ctx: "TurnContext", narration: str) -> str | None:
    """Sends the DM back when a say tag can't stand (D76)."""
    problems = [
        f"<say who={line.tag.attrs.get('who', '')[:40]!r}>: {line.problem}"
        for line in check_speech(ctx, narration)
        if line.problem
    ]
    stripped = SAY.sub("", narration)
    if re.search(r"</?say\b", stripped, re.IGNORECASE):
        problems.append("a say tag is not closed: every <say ...> needs its </say>")
    if not problems:
        return None
    return (
        "<rules_check>Some speech can't be shown as written: "
        + "; ".join(problems)
        + '. Every line anyone other than the player character speaks goes in <say who="..." '
        'lang="..." tone="..." gist="...">words</say>, and only someone here who speaks that '
        "language can say it. Fix the tags without rolling again, then tell the turn once, "
        "from the start: this telling replaces your earlier one.</rules_check>"
    )


def render_line(ctx: "TurnContext", line: Line, listener: str) -> str:
    """What the listening character gets of one line (D77)."""
    if line.problem is not None or line.language is None:
        return f"[words {listener} can't make out]"
    if line.heard is Heard.FLUENT:
        return f'"{line.tag.words}"'
    lang = ctx.content.languages[line.language]
    where = f"in {lang.name}" if lang.common else f"in a language {listener} doesn't know"
    tone = line.tag.attrs.get("tone")
    gist = line.tag.attrs.get("gist")
    if line.heard is Heard.GIST:
        parts = [where, f"sounding {tone}" if tone else None]
        head = ", ".join(p for p in parts if p)
        return f"[{head}; the gist: {gist}]" if gist else f"[{head}]"
    if line.heard is Heard.TONE:
        return f"[something {where}, sounding {tone}]" if tone else f"[something {where}]"
    if lang.sounds:
        noise = gibberish(line.tag.words, lang.sounds, salt=lang.id)
        return f'"{noise}" [{where}]'
    return f"[something {where}]"


def render(ctx: "TurnContext", narration: str, lines: list[Line]) -> str:
    listener = characters.get_character(ctx.conn, ctx.character_id).name
    out, cursor = [], 0
    for line in lines:
        out += [narration[cursor : line.tag.start], render_line(ctx, line, listener)]
        cursor = line.tag.end
    out.append(narration[cursor:])
    shown = "".join(out)
    # Anything left of a broken tag could be untranslated words: never show it.
    shown = UNCLOSED.sub(f"[words {listener} can't make out]", shown)
    return STRAY_CLOSE.sub("", shown)


def finish_speech(ctx: "TurnContext", narration: str) -> str:
    """Log every line with what the character understood; return what the player sees."""
    lines = check_speech(ctx, narration)
    for line in lines:
        if not line.tag.words or len(line.tag.words) > speech.MAX_WORDS:
            continue
        try:
            speech.record_line(
                ctx.conn,
                ctx.scene_id,
                ctx.character_id,
                speaker=line.speaker or "someone",
                npc_id=line.npc_id,
                language_id=line.language,
                words=line.tag.words,
                tone=_fits(line.tag.attrs.get("tone"), speech.MAX_TONE),
                gist=_fits(line.tag.attrs.get("gist"), speech.MAX_GIST),
                heard=line.heard,
            )
        except (RulesError, ValueError):
            continue  # a line that can't be logged is still never shown untranslated
    return render(ctx, narration, lines)


def _fits(value: str | None, limit: int) -> str | None:
    return value if value and len(value) <= limit else None


def for_dm(ctx: "TurnContext", me: Character) -> dict[str, Any]:
    """Speech state for the DM: what the character speaks and has understood here."""
    names = {lang.id: lang.name for lang in ctx.content.languages.values()}
    return {
        "character_speaks_aloud": names.get(me.speaking, me.speaking),
        "understood_this_scene": {names[k]: v.value for k, v in earned(ctx).items()},
        "recent_lines": [
            {
                "who": line.speaker,
                "language": names.get(line.language_id or "", "unknown"),
                "words": line.words,
                "character_understood": line.heard.value,
            }
            for line in speech.lines_in_scene(
                ctx.conn, ctx.scene_id, ctx.character_id, limit=RECENT_LINES
            )
        ],
    }
