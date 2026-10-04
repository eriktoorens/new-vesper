"""A single-player play session: the loop between the terminal and the DM agent.

No terminal I/O here, so the whole loop is testable with a stubbed model. Each
player turn is one beat: open it, record the intent, run the agent, resolve it
with narration and a one-line summary. Older beats fold into the scene summary
so the prompt stays short.

Every model call is priced and written to the usage ledger against this player
and scene, and the budget is checked before each call (D21, D22).
"""

import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from new_vesper.budget.ledger import record_call
from new_vesper.budget.policy import BudgetConfig, BudgetExhausted, BudgetStatus, budget_status
from new_vesper.budget.pricing import PRICES, ModelPrice, price_of
from new_vesper.city.encounters import ideas_here, left_today, recent_in_district
from new_vesper.city.npcs import present_at, settle
from new_vesper.city.sky import season, tide_at
from new_vesper.city.tick import run_due_ticks
from new_vesper.city.weather import current_weather
from new_vesper.content.loader import Content
from new_vesper.dm import needs as bodily
from new_vesper.dm import prompt, speech, story
from new_vesper.dm.agent import ModelClient, TurnResult, UsageHook, run_turn, summarize
from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.handlers import (
    TurnContext,
    apply_needs,
    describe_character,
    describe_location,
    dispatch,
    owed_reminder,
)
from new_vesper.dm.tools import TOOLS
from new_vesper.rules import clock
from new_vesper.rules.character import resolve_full_harm
from new_vesper.rules.currency import format_glitter
from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import RulesError
from new_vesper.rules.leveling import LevelUpRequest, level_up
from new_vesper.rules.needs import Need
from new_vesper.rules.sky import moon
from new_vesper.rules.tracks import must_fall_or_endure
from new_vesper.state import attitudes, characters, scenes, world
from new_vesper.state import needs as stored_needs
from new_vesper.state.characters import Character
from new_vesper.state.errors import StateError
from new_vesper.state.events import Actor, Cause, Event, append_event, list_events

ARRIVAL = (
    "The player's character has just arrived here. Set the scene in a few sentences: the "
    "place, who is around, one thing that invites action. No roll."
)
SECONDS_PER_DAY = 86_400
# Events the recap leaves out: bookkeeping, or things the character couldn't know
# (an NPC's private progress surfaces in play through what the DM sees instead).
PRIVATE_EVENTS = frozenset(
    {
        "roll",
        "presence_changed",
        "npc_goal_advanced",
        "npc_met",
        "neglect",
        "details_set",
        "speaking_changed",
        "needs_relieved",
    }
)
# Memory lines each NPC keeps per character before older ones fold into a summary.
MEMORIES_KEPT = 8
# One action per prompt (D99): refused whole, so nothing of it reaches the DM.
ONE_LINE = "One action at a time, on one line. None of that was sent; try again."
# Where exported stories go, next to the world's database by default (D104).
STORIES = Path("stories")
QUIET_NARRATION = "The rain goes quiet, and so does the city. {message}"


class SessionError(Exception):
    """A player command the session refuses. The message is shown to the player."""


@dataclass
class TurnOutcome:
    narration: str
    fall_or_endure_pending: bool = False
    slipped: bool = False
    changes: tuple[str, ...] = ()
    can_level_up: bool = False
    # The budget ran out during this turn; the city has gone quiet.
    quiet: bool = False
    # ASCII art to show before the narration: a new place, a new face.
    art: tuple[str, ...] = ()
    # The city clock and weather where the character is: 'Tuesday 9:40 pm, evening; Fog'.
    status: str = ""


def art_block(caption: str, lines: tuple[str, ...]) -> str:
    """ASCII art with a caption underneath."""
    return "\n".join([*lines, f"  -- {caption} --"])


def _parse_time(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


class PlaySession:
    def __init__(
        self,
        conn: sqlite3.Connection,
        content: Content,
        client: ModelClient,
        design_text: str,
        rng: Rng,
        character_id: int,
        *,
        config: DMConfig | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        on_usage: UsageHook | None = None,
        budget: BudgetConfig | None = None,
        prices: Mapping[str, ModelPrice] = PRICES,
    ) -> None:
        self.conn = conn
        self.content = content
        self.client = client
        self.rng = rng
        self.config = config or DMConfig()
        self.now = now
        self.observer = on_usage
        self.budget = budget or BudgetConfig()
        self.prices = prices
        for call in CallType:
            # Refuse up front: an unpriced model's spend could not be recorded.
            price_of(self.config.model_for(call), prices)
        self.system = prompt.system_prompt(design_text, content)
        self.character_id = character_id
        self.player_id = characters.get_character(conn, character_id).player_id
        self.scene_id: int | None = None
        # NPCs who were present at some point in the current scene.
        self.scene_npcs: set[str] = set()

    # --- budget ------------------------------------------------------------

    def budget_status(self) -> BudgetStatus:
        return budget_status(self.conn, self.budget, self.player_id, self.now())

    def _guard(self) -> None:
        """Runs before every model call: no call once a limit is reached."""
        status = self.budget_status()
        if not status.can_play:
            raise BudgetExhausted(status.blocked_message())

    def on_usage(self, call: CallType, model: str, usage: Any) -> None:
        """Record every call against this player and scene."""
        record_call(
            self.conn,
            call,
            model,
            usage,
            player_id=self.player_id,
            scene_id=self.scene_id,
            prices=self.prices,
        )
        if self.observer is not None:
            self.observer(call, model, usage)

    def _summarize(self, call: CallType, request: str) -> str:
        """A cheap summary call; empty if the budget is spent, so callers fall back."""
        try:
            return summarize(self.client, self.config, call, request, self.on_usage, self._guard)
        except BudgetExhausted:
            return ""

    def _require_budget(self) -> None:
        status = self.budget_status()
        if not status.can_play:
            raise SessionError(status.blocked_message())

    # --- helpers -----------------------------------------------------------

    @property
    def character(self) -> Character:
        return characters.get_character(self.conn, self.character_id)

    def _cause(self, actor: Actor = Actor.PLAYER) -> Cause:
        return Cause(actor, self.player_id, self.scene_id)

    def _context(self) -> TurnContext:
        assert self.scene_id is not None
        return TurnContext(
            self.conn,
            self.content,
            self.rng,
            self.character_id,
            self.player_id,
            self.scene_id,
            now=self.now(),
        )

    def _state(self, ctx: TurnContext) -> dict[str, Any]:
        assert self.scene_id is not None
        scene = scenes.get_scene(self.conn, self.scene_id)
        me = self.character
        recent = scenes.recent_beats(self.conn, scene.id, limit=self.config.recent_beats)
        sky = current_weather(self.conn, self.content, scene.region_id, ctx.now)
        return {
            "time": clock.describe(ctx.now),
            "weather": {"now": sky.name, "description": sky.description},
            "encounters": {
                "left_today_in_district": left_today(self.conn, scene.region_id, ctx.now),
                "ideas_that_fit_here": ideas_here(self.conn, self.content, me.location_id, ctx.now)
                if me.location_id
                else [],
                "recently_in_district": recent_in_district(self.conn, scene.region_id, ctx.now),
            },
            "character": describe_character(ctx, me),
            "location": describe_location(ctx, me.location_id) if me.location_id else None,
            "speech": speech.for_dm(ctx, me),
            "scene": {
                "id": scene.id,
                "region": scene.region_id,
                "summary_of_earlier_beats": scene.summary,
                "recent_beats": [{"number": b.number, "summary": b.summary} for b in recent],
                "last_narration": recent[-1].narration if recent else None,
            },
        }

    def _open_scene(self) -> None:
        me = self.character
        if me.location_id is None:
            raise SessionError("this character is nowhere; move them first")
        region = world.get_location(self.conn, me.location_id).region_id
        scene = scenes.open_scene(
            self.conn, region, self._cause(Actor.SYSTEM), location_id=me.location_id
        )
        self.scene_id = scene.id
        scenes.join_scene(self.conn, scene.id, me.id, self._cause(Actor.SYSTEM))

    def _close_scene(self) -> None:
        if self.scene_id is None:
            return
        scene = scenes.get_scene(self.conn, self.scene_id)
        if scene.open:
            self._remember_scene(scene.id)
            recent = scenes.recent_beats(self.conn, scene.id, limit=self.config.recent_beats)
            parts = [scene.summary, *(b.summary for b in recent)]
            summary = " ".join(p for p in parts if p).strip() or "Nothing of note happened."
            scenes.close_scene(self.conn, scene.id, summary[:2000], self._cause(Actor.SYSTEM))
        self.scene_id = None

    def _remember_scene(self, scene_id: int) -> None:
        """When a scene closes, each NPC who was there keeps a line about the character (D63)."""
        npcs, self.scene_npcs = self.scene_npcs, set()
        acted = self.conn.execute(
            "SELECT COUNT(*) FROM beat_intents i JOIN beats b ON b.id = i.beat_id"
            " WHERE b.scene_id = ? AND i.intent IS NOT NULL",
            (scene_id,),
        ).fetchone()[0]
        if not npcs or not acted:
            return
        me = self.character
        beats = self.conn.execute(
            "SELECT summary FROM beats WHERE scene_id = ? AND status = 'resolved' ORDER BY number",
            (scene_id,),
        ).fetchall()
        scene = [scenes.get_scene(self.conn, scene_id).summary] + [b[0] for b in beats]
        names = {n: self.content.npcs[n].name for n in sorted(npcs)}
        reply = self._summarize(
            CallType.NPC_MEMORY, prompt.memory_request(me.name, names, [s for s in scene if s])
        )
        cause = Cause(Actor.SYSTEM, self.player_id, scene_id)
        for npc_id, note in prompt.parse_memory_lines(reply, set(names)).items():
            attitudes.add_memory(self.conn, npc_id, me.id, note, cause)
            self._fold_memories(npc_id, me)

    def _fold_memories(self, npc_id: str, me: Character) -> None:
        old = attitudes.notes_to_fold(self.conn, npc_id, me.id, keep=MEMORIES_KEPT)
        if not old:
            return
        earlier = attitudes.memory_of(self.conn, npc_id, me.id).summary
        name = self.content.npcs[npc_id].name
        merged = self._summarize(
            CallType.NPC_MEMORY,
            prompt.fold_memory_request(name, me.name, earlier, [n for _, n in old]),
        ) or " ".join(filter(None, [earlier, *(n for _, n in old)]))
        attitudes.fold_memories(self.conn, npc_id, me.id, [i for i, _ in old], merged[:600])

    def _run(self, intent: str | None, direction: str | None) -> TurnOutcome:
        """One beat: record the intent, run the agent, resolve the beat."""
        assert self.scene_id is not None
        beat = scenes.open_beat(self.conn, self.scene_id, self._cause(Actor.SYSTEM))
        if intent is not None:
            scenes.submit_intent(self.conn, beat.id, self.character_id, intent, self._cause())
        ctx = self._context()
        # The time since the last turn counts against the character's needs (D85).
        apply_needs(ctx)
        self.scene_npcs |= {
            w.npc.id
            for w in present_at(self.conn, self.content, self.character.location_id or "", ctx.now)
        }
        message = prompt.turn_message(self._state(ctx), intent, direction)
        quiet = False
        try:
            result: TurnResult = run_turn(
                self.client,
                self.config,
                self.system,
                message,
                lambda name, raw: dispatch(ctx, name, raw),
                self.on_usage,
                self._guard,
                completion=lambda text: owed_reminder(ctx) or speech.speech_reminder(ctx, text),
            )
        except BudgetExhausted as exc:
            # Tool calls already made stand: each was complete and rule-checked.
            quiet = True
            result = TurnResult(narration=QUIET_NARRATION.format(message=exc))
        except BaseException:
            # Never leave the region blocked by an open beat.
            scenes.resolve_beat(
                self.conn,
                beat.id,
                "(The turn failed before it could be told.)",
                "The turn failed.",
                self._cause(Actor.SYSTEM),
            )
            raise
        # The player sees, and the beat keeps, only what the character understood (D81).
        result.narration = speech.finish_speech(ctx, result.narration)
        summary = (
            self._summarize(
                CallType.BEAT_SUMMARY, prompt.beat_summary_request(intent, result.narration)
            )
            or result.narration[:200]
        )
        scenes.resolve_beat(
            self.conn, beat.id, result.narration, summary[:2000], self._cause(Actor.DM)
        )
        self._fold(beat.number)
        me = self.character
        return TurnOutcome(
            status=self.status_line(),
            narration=result.narration,
            fall_or_endure_pending=ctx.fall_or_endure_pending
            or (must_fall_or_endure(me.sheet.harm) and not me.sheet.fallen),
            slipped=ctx.slipped,
            changes=tuple(ctx.changes),
            can_level_up=describe_character(ctx, me)["can_level_up"],
            quiet=quiet,
        )

    def _fold(self, latest: int) -> None:
        """Fold the beat that just left the recent window into the scene summary."""
        assert self.scene_id is not None
        leaving = latest - self.config.recent_beats
        if leaving < 1:
            return
        row = self.conn.execute(
            "SELECT summary FROM beats WHERE scene_id = ? AND number = ?", (self.scene_id, leaving)
        ).fetchone()
        scene = scenes.get_scene(self.conn, self.scene_id)
        if row is None:
            return
        folded = (
            self._summarize(
                CallType.SCENE_SUMMARY, prompt.fold_summary_request(scene.summary, row[0])
            )
            or f"{scene.summary} {row[0]}".strip()
        )
        scenes.update_scene_summary(
            self.conn, self.scene_id, folded[:2000], self._cause(Actor.SYSTEM)
        )

    # --- art -----------------------------------------------------------------

    def _arrival_art(self) -> tuple[str, ...]:
        """Before opening a scene: the place's vignette on a first visit, new faces' portraits.

        Portraits show once per character, the first time they share a place with the NPC.
        """
        me = self.character
        if me.location_id is None:
            return ()
        place = self.content.locations[me.location_id]
        blocks = []
        if place.id not in characters.played_locations(self.conn, me.id):
            blocks.append(art_block(place.name, place.art))
        met = {
            e.payload.get("npc_id")
            for e in list_events(self.conn, character_id=me.id, kind="npc_met", limit=100_000)
        }
        for npc in (w.npc for w in present_at(self.conn, self.content, place.id, self.now())):
            if npc.id not in met:
                blocks.append(art_block(npc.name, npc.portrait))
                append_event(
                    self.conn,
                    "npc_met",
                    self._cause(Actor.SYSTEM),
                    {"npc_id": npc.id},
                    character_id=me.id,
                )
        return tuple(blocks)

    @staticmethod
    def _with_art(outcome: TurnOutcome, art: tuple[str, ...]) -> TurnOutcome:
        return replace(outcome, art=art)

    def status_line(self) -> str:
        """The city clock and the weather where the character is."""
        now = self.now()
        me = self.character
        if me.location_id is None:
            return clock.describe(now)
        place = self.content.locations[me.location_id]
        weather = current_weather(self.conn, self.content, place.region_id, now)
        parts = [clock.describe(now)]
        current = season(self.content, now)
        if current is not None:
            parts.append(current.name)
        parts += [weather.name, moon(now).phase]
        felt = bodily.summary(bodily.levels(self.conn, self.content, me))
        here = tide_at(place.tide, now)
        if here is not None:
            turning = ", turning" if here.tide.turning else ""
            spring = " spring" if here.tide.spring else ""
            parts.append(f"{here.tide.state.value}{spring} tide{turning}")
        if felt:
            parts.append(felt)
        return "; ".join(parts)

    def who(self) -> list[str]:
        """Who is here right now and what they're visibly doing."""
        me = self.character
        present = present_at(self.conn, self.content, me.location_id or "", self.now())
        return [f"{w.npc.name}: {w.activity}" for w in present]

    def location_art(self) -> str | None:
        me = self.character
        if me.location_id is None:
            return None
        place = self.content.locations[me.location_id]
        return art_block(place.name, place.art)

    # --- lifecycle -----------------------------------------------------------

    def _last_logoff(self) -> Event | None:
        events = list_events(
            self.conn, character_id=self.character_id, kind="presence_changed", limit=100_000
        )
        offline = [e for e in events if e.payload.get("online") is False]
        return offline[-1] if offline else None

    def _recover(self, logoff: Event) -> list[str]:
        """Resting at a haven clears 1 Harm and 1 Fade per real day offline (D8)."""
        me = self.character
        if me.location_id is None or not world.get_location(self.conn, me.location_id).is_haven:
            return []
        days = int((self.now() - _parse_time(logoff.created_at)).total_seconds() // SECONDS_PER_DAY)
        harm, fade = min(days, me.sheet.harm), min(days, me.sheet.fade)
        if me.sheet.fallen or (harm == 0 and fade == 0):
            return []
        after = replace(me.sheet, harm=me.sheet.harm - harm, fade=me.sheet.fade - fade)
        characters.update_sheet(
            self.conn, me.id, me.sheet, after, self._cause(Actor.SYSTEM), f"rested {days} days"
        )
        return [f"rested: -{harm} Harm, -{fade} Fade"]

    def _recap(self, logoff: Event) -> str | None:
        """What changed while away: events after logoff that this player didn't cause."""
        events = [
            e
            for e in list_events(self.conn, after_id=logoff.id, limit=200)
            if e.player_id != self.player_id and e.kind not in PRIVATE_EVENTS
        ]
        if not events:
            return None
        brief = [{"kind": e.kind, "region": e.region_id, **e.payload} for e in events[-40:]]
        return self._summarize(CallType.RECAP, prompt.recap_request(brief)) or None

    def start(self) -> tuple[str | None, list[str], TurnOutcome]:
        """Come online, recover at a haven, open a scene and describe it.

        Returns (recap of what changed while away, recovery notes, the opening).
        """
        me = self.character
        if me.sheet.fallen:
            raise SessionError(f"{me.name} has fallen; their story is over")
        self._require_budget()
        run_due_ticks(self.conn, self.content, self.now())
        logoff = self._last_logoff()
        # NPCs went about their day while nobody was here (D113).
        settle(self.conn, self.content, self.now(), arriving=me.id)
        characters.set_online(self.conn, me.id, True, self._cause())
        # Needs pick up where they were at logoff: offline time never counts (D88).
        stored_needs.resume(self.conn, me.id, sorted(bodily.needs_of(self.content, me)), self.now())
        notes = self._recover(logoff) if logoff else []
        recap = self._recap(logoff) if logoff else None
        art = self._arrival_art()
        self._open_scene()
        return recap, notes, self._with_art(self._run(None, ARRIVAL), art)

    def turn(self, intent: str) -> TurnOutcome:
        me = self.character
        if me.sheet.fallen:
            raise SessionError(f"{me.name} has fallen; their story is over")
        if must_fall_or_endure(me.sheet.harm):
            raise SessionError("choose Fall or Endure first")
        if not intent.strip():
            raise SessionError("say what your character does")
        if not scenes.one_line(intent):
            raise SessionError(ONE_LINE)
        if len(intent) > scenes.MAX_INTENT_LENGTH:
            raise SessionError(f"keep it under {scenes.MAX_INTENT_LENGTH} characters")
        self._require_budget()
        run_due_ticks(self.conn, self.content, self.now())  # a session can cross midnight
        return self._run(intent, None)

    def ask(self, question: str) -> str:
        """An out-of-character question. The DM may only look; nothing changes, no beat."""
        if not question.strip():
            raise SessionError("ask a question after /ask")
        if not scenes.one_line(question):
            raise SessionError(ONE_LINE)
        if len(question) > scenes.MAX_INTENT_LENGTH:
            raise SessionError(f"keep it under {scenes.MAX_INTENT_LENGTH} characters")
        self._require_budget()
        ctx = self._context()
        look_only = [dict(t) for t in TOOLS if t["name"] == "look"]
        look_only[0]["cache_control"] = {"type": "ephemeral"}

        def only_look(name: str, raw: Any) -> tuple[dict[str, Any], bool]:
            if name != "look":
                return {"error": "only look is available while answering a question"}, True
            return dispatch(ctx, name, raw)

        try:
            result = run_turn(
                self.client,
                self.config,
                self.system,
                prompt.ask_message(self._state(ctx), question),
                only_look,
                self.on_usage,
                self._guard,
                tools=look_only,
            )
        except BudgetExhausted as exc:
            raise SessionError(str(exc)) from exc
        return speech.render(ctx, result.narration, speech.check_speech(ctx, result.narration))

    def rename(self, name: str) -> Character:
        """Change the character's name (D107). The old name stays in the event log."""
        if not name:
            raise SessionError("give the new name after /rename")
        try:
            return characters.rename_character(self.conn, self.character_id, name, self._cause())
        except StateError as exc:
            raise SessionError(str(exc)) from exc

    def set_pronouns(self, pronouns: str) -> Character:
        if not pronouns:
            raise SessionError("give the pronouns after /pronouns, e.g. /pronouns it/its")
        try:
            return characters.set_pronouns(self.conn, self.character_id, pronouns, self._cause())
        except StateError as exc:
            raise SessionError(str(exc)) from exc

    def speak(self, language: str) -> Character:
        """Choose the language the character speaks aloud, from those they know (D80)."""
        me = self.character
        key = language.strip().casefold()
        match = next(
            (
                lang.id
                for lang in self.content.languages.values()
                if key in (lang.id, lang.name.casefold())
            ),
            None,
        )
        if match is None or match not in me.speaks:
            known = ", ".join(self.content.languages[lang].name for lang in sorted(me.speaks))
            raise SessionError(f"{me.name} speaks {known}")
        return characters.set_speaking(self.conn, me.id, match, self._cause())

    # --- stories ---------------------------------------------------------------

    def export(self, kind: str = "telling", folder: Path = STORIES) -> Path:
        """Save the character's story: the record as seen, or the telling in their voice.

        Both are built only from what the player was shown (D101). The telling is one
        cheap model call, priced and checked against the budget like any other (D102).
        """
        me = self.character
        told = story.chapters(self.conn, self.content, me.id)
        if kind == "record":
            text = story.record(me, self.content, told)
        elif kind == "telling":
            if not told:
                raise SessionError("there's no story to tell yet")
            self._require_budget()
            try:
                words = summarize(
                    self.client,
                    self.config,
                    CallType.STORY,
                    story.telling_request(me, self.content, told),
                    self.on_usage,
                    self._guard,
                    system=story.STORY_SYSTEM,
                    max_tokens=self.config.story_max_tokens,
                )
            except BudgetExhausted as exc:
                raise SessionError(str(exc)) from exc
            if not words.strip():
                raise SessionError("the story wouldn't come out right; /export record still works")
            text = story.telling(me, self.content, words)
        else:
            raise SessionError("export a telling or a record")
        return story.write(folder, me, kind, text, self.now())

    # --- needs ---------------------------------------------------------------

    def _provide(self, need: Need, verb: str) -> str:
        """Eat or drink what this place sells, paying its price (D87)."""
        me = self.character
        if me.sheet.fallen or must_fall_or_endure(me.sheet.harm):
            raise SessionError("not now")
        if need not in bodily.needs_of(self.content, me):
            raise SessionError(f"{me.name} doesn't need to {verb}")
        place = self.content.locations.get(me.location_id or "")
        offer = place.provisions.get(need) if place is not None else None
        if offer is None:
            raise SessionError(f"nobody here sells anything to {verb}")
        if offer.price > me.currency:
            raise SessionError(
                f"{offer.what} costs {format_glitter(offer.price)}; "
                f"{me.name} has {format_glitter(me.currency)}"
            )
        if offer.price:
            characters.adjust_currency(
                self.conn, me.id, -offer.price, self._cause(), f"{verb}: {offer.what}"
            )
        stored_needs.relieve(self.conn, me.id, [need], self.now(), self._cause(), offer.what)
        paid = f" for {format_glitter(offer.price)}" if offer.price else ""
        return f"{me.name} has {offer.what}{paid}."

    def eat(self) -> str:
        return self._provide(Need.HUNGER, "eat")

    def drink(self) -> str:
        return self._provide(Need.THIRST, "drink")

    def rest(self) -> str:
        """Sleep at a haven: tiredness clears (D87)."""
        me = self.character
        if me.sheet.fallen or must_fall_or_endure(me.sheet.harm):
            raise SessionError("not now")
        if Need.TIRED not in bodily.needs_of(self.content, me):
            raise SessionError(f"{me.name} doesn't need sleep")
        if me.location_id is None or not world.get_location(self.conn, me.location_id).is_haven:
            raise SessionError("you can only rest safely at a haven")
        stored_needs.relieve(
            self.conn, me.id, [Need.TIRED], self.now(), self._cause(), "slept at a haven"
        )
        return f"{me.name} sleeps, and wakes rested."

    def fall_or_endure(self, choice: str, scar: str | None = None) -> Character:
        """The player's choice at full Harm. Death is only ever this choice."""
        me = self.character
        try:
            after = resolve_full_harm(me.sheet, choice, scar)
        except RulesError as exc:
            raise SessionError(str(exc)) from exc
        return characters.update_sheet(
            self.conn, me.id, me.sheet, after, self._cause(), f"chose {choice}"
        )

    def level(self, request: LevelUpRequest) -> Character:
        """A level-up the player chose from the menu (D17)."""
        me = self.character
        try:
            after = level_up(me.sheet, request)
            return characters.update_sheet(
                self.conn, me.id, me.sheet, after, self._cause(), f"level {after.level}"
            )
        except (RulesError, StateError) as exc:
            raise SessionError(str(exc)) from exc

    def go(self, location_id: str) -> TurnOutcome:
        """Move to another place in the same region: a new scene there."""
        me = self.character
        if must_fall_or_endure(me.sheet.harm) or me.sheet.fallen:
            raise SessionError("you can't go anywhere right now")
        target = self.content.locations.get(location_id)
        if target is None:
            raise SessionError(f"no place called {location_id[:40]!r}")
        here = self.content.locations[me.location_id] if me.location_id else None
        if here is not None and here.region_id != target.region_id:
            raise SessionError("that's in another district")
        if here is not None and here.id == target.id:
            raise SessionError("you're already there")
        flooded = tide_at(target.tide, self.now())
        if flooded is not None and flooded.closed:
            nxt = clock.describe(flooded.tide.next_low)
            raise SessionError(f"{target.name} is under water right now; low water is {nxt}")
        self._require_budget()
        self._close_scene()
        # Whoever is at the new place is there as of now, before the character watches it.
        settle(self.conn, self.content, self.now())
        characters.move_character(self.conn, me.id, target.id, self._cause())
        art = self._arrival_art()
        self._open_scene()
        return self._with_art(self._run(None, ARRIVAL), art)

    def end(self) -> None:
        """Log off: close the scene and go offline (safe at a haven, lying low elsewhere).

        Logging off at a haven clears every need (D88).
        """
        me = self.character
        if me.location_id is not None and world.get_location(self.conn, me.location_id).is_haven:
            needs = sorted(bodily.needs_of(self.content, me))
            felt = bodily.levels(self.conn, self.content, me)
            if any(felt.values()):
                stored_needs.relieve(
                    self.conn, me.id, needs, self.now(), self._cause(), "rested at a haven"
                )
        self._close_scene()
        characters.set_online(self.conn, self.character_id, False, self._cause())
