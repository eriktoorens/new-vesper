"""A single-player play session: the loop between the terminal and the DM agent.

No terminal I/O here, so the whole loop is testable with a stubbed model. Each
player turn is one beat: open it, record the intent, run the agent, resolve it
with narration and a one-line summary. Older beats fold into the scene summary
so the prompt stays short.
"""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from new_vesper.content.loader import Content
from new_vesper.dm import prompt
from new_vesper.dm.agent import ModelClient, TurnResult, UsageHook, run_turn, summarize
from new_vesper.dm.config import CallType, DMConfig
from new_vesper.dm.handlers import TurnContext, describe_character, describe_location, dispatch
from new_vesper.rules.character import resolve_full_harm
from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import RulesError
from new_vesper.rules.leveling import LevelUpRequest, level_up
from new_vesper.rules.tracks import must_fall_or_endure
from new_vesper.state import characters, scenes, world
from new_vesper.state.characters import Character
from new_vesper.state.errors import StateError
from new_vesper.state.events import Actor, Cause, Event, list_events

ARRIVAL = (
    "The player's character has just arrived here. Set the scene in a few sentences: the "
    "place, who is around, one thing that invites action. No roll."
)
SECONDS_PER_DAY = 86_400


class SessionError(Exception):
    """A player command the session refuses. The message is shown to the player."""


@dataclass
class TurnOutcome:
    narration: str
    fall_or_endure_pending: bool = False
    slipped: bool = False
    changes: tuple[str, ...] = ()
    can_level_up: bool = False


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
    ) -> None:
        self.conn = conn
        self.content = content
        self.client = client
        self.rng = rng
        self.config = config or DMConfig()
        self.now = now
        self.on_usage = on_usage
        self.system = prompt.system_prompt(design_text, content)
        self.character_id = character_id
        self.player_id = characters.get_character(conn, character_id).player_id
        self.scene_id: int | None = None

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
        return {
            "character": describe_character(ctx, me),
            "location": describe_location(ctx, me.location_id) if me.location_id else None,
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
            recent = scenes.recent_beats(self.conn, scene.id, limit=self.config.recent_beats)
            parts = [scene.summary, *(b.summary for b in recent)]
            summary = " ".join(p for p in parts if p).strip() or "Nothing of note happened."
            scenes.close_scene(self.conn, scene.id, summary[:2000], self._cause(Actor.SYSTEM))
        self.scene_id = None

    def _run(self, intent: str | None, direction: str | None) -> TurnOutcome:
        """One beat: record the intent, run the agent, resolve the beat."""
        assert self.scene_id is not None
        beat = scenes.open_beat(self.conn, self.scene_id, self._cause(Actor.SYSTEM))
        if intent is not None:
            scenes.submit_intent(self.conn, beat.id, self.character_id, intent, self._cause())
        ctx = self._context()
        message = prompt.turn_message(self._state(ctx), intent, direction)
        try:
            result: TurnResult = run_turn(
                self.client,
                self.config,
                self.system,
                message,
                lambda name, raw: dispatch(ctx, name, raw),
                self.on_usage,
            )
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
        summary = (
            summarize(
                self.client,
                self.config,
                CallType.BEAT_SUMMARY,
                prompt.beat_summary_request(intent, result.narration),
                self.on_usage,
            )
            or result.narration[:200]
        )
        scenes.resolve_beat(
            self.conn, beat.id, result.narration, summary[:2000], self._cause(Actor.DM)
        )
        self._fold(beat.number)
        me = self.character
        return TurnOutcome(
            narration=result.narration,
            fall_or_endure_pending=ctx.fall_or_endure_pending
            or (must_fall_or_endure(me.sheet.harm) and not me.sheet.fallen),
            slipped=ctx.slipped,
            changes=tuple(ctx.changes),
            can_level_up=describe_character(ctx, me)["can_level_up"],
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
            summarize(
                self.client,
                self.config,
                CallType.SCENE_SUMMARY,
                prompt.fold_summary_request(scene.summary, row[0]),
                self.on_usage,
            )
            or f"{scene.summary} {row[0]}".strip()
        )
        scenes.update_scene_summary(
            self.conn, self.scene_id, folded[:2000], self._cause(Actor.SYSTEM)
        )

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
            if e.player_id != self.player_id and e.kind not in {"roll", "presence_changed"}
        ]
        if not events:
            return None
        brief = [{"kind": e.kind, "region": e.region_id, **e.payload} for e in events[-40:]]
        return (
            summarize(
                self.client, self.config, CallType.RECAP, prompt.recap_request(brief), self.on_usage
            )
            or None
        )

    def start(self) -> tuple[str | None, list[str], TurnOutcome]:
        """Come online, recover at a haven, open a scene and describe it.

        Returns (recap of what changed while away, recovery notes, the opening).
        """
        me = self.character
        if me.sheet.fallen:
            raise SessionError(f"{me.name} has fallen; their story is over")
        logoff = self._last_logoff()
        characters.set_online(self.conn, me.id, True, self._cause())
        notes = self._recover(logoff) if logoff else []
        recap = self._recap(logoff) if logoff else None
        self._open_scene()
        return recap, notes, self._run(None, ARRIVAL)

    def turn(self, intent: str) -> TurnOutcome:
        me = self.character
        if me.sheet.fallen:
            raise SessionError(f"{me.name} has fallen; their story is over")
        if must_fall_or_endure(me.sheet.harm):
            raise SessionError("choose Fall or Endure first")
        if not intent.strip():
            raise SessionError("say what your character does")
        if len(intent) > scenes.MAX_INTENT_LENGTH:
            raise SessionError(f"keep it under {scenes.MAX_INTENT_LENGTH} characters")
        return self._run(intent, None)

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
        self._close_scene()
        characters.move_character(self.conn, me.id, target.id, self._cause())
        self._open_scene()
        return self._run(None, ARRIVAL)

    def end(self) -> None:
        """Log off: close the scene and go offline (safe at a haven, lying low elsewhere)."""
        self._close_scene()
        characters.set_online(self.conn, self.character_id, False, self._cause())
