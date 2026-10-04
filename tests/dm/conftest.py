"""A stub model client and a seeded world for DM tests. No network, ever."""

import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from new_vesper.content.loader import Content, load_content
from new_vesper.content.seed import seed
from new_vesper.dm.handlers import TurnContext
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.stats import Stat
from new_vesper.state import characters, players, scenes
from new_vesper.state.characters import Character
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM

# A Tuesday at noon on the city clock (US Eastern): Tomás is at his cart,
# Nana Priya is cleaning bunks at the Hooks.
NOON_TUESDAY = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)

DESIGN_TEXT = (Path(__file__).resolve().parents[2] / "docs" / "design.md").read_text()
STATS = {Stat.STEEL: 1, Stat.SLICK: 2, Stat.WIRE: 1, Stat.WEIRD: 0, Stat.HEART: -1}


@dataclass
class Block:
    type: str
    text: str | None = None
    id: str | None = None
    name: str | None = None
    input: Any = None


@dataclass
class Usage:
    input_tokens: int = 100
    output_tokens: int = 50
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class Response:
    content: list[Block]
    stop_reason: str
    usage: Usage = field(default_factory=Usage)


def say(text: str) -> Response:
    return Response([Block("text", text=text)], "end_turn")


def use(*calls: tuple[str, dict[str, Any]], text: str | None = None) -> Response:
    blocks = [Block("thinking", text=None)]
    if text:
        blocks.append(Block("text", text=text))
    blocks += [
        Block("tool_use", id=f"toolu_{i}", name=name, input=args)
        for i, (name, args) in enumerate(calls)
    ]
    return Response(blocks, "tool_use")


Step = Response | Callable[[dict[str, Any]], Response]


class StubMessages:
    """Scripted turn responses; summary calls (no tools) get a canned summary."""

    def __init__(self, script: list[Step]) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []
        # What no-tools (summary) calls answer; tests can replace it.
        self.summary: Callable[[dict[str, Any]], str] = lambda kwargs: "A short summary."

    def create(self, **kwargs: Any) -> Response:
        self.calls.append(kwargs)
        if "tools" not in kwargs:
            return say(self.summary(kwargs))
        if not self.script:
            return say("The rain keeps falling.")
        step = self.script.pop(0)
        return step(kwargs) if callable(step) else step

    @property
    def turn_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if "tools" in c]


class StubClient:
    def __init__(self, *script: Step) -> None:
        self.messages = StubMessages(list(script))


class SeqRng:
    """Returns scripted values; checks each fits the range asked for."""

    def __init__(self, *values: int) -> None:
        self.values = list(values)

    def randint(self, a: int, b: int) -> int:
        value = self.values.pop(0)
        assert a <= value <= b, (value, a, b)
        return value


@pytest.fixture(scope="session")
def content() -> Content:
    return load_content()


@pytest.fixture
def conn(content: Content) -> Iterator[sqlite3.Connection]:
    db = open_database()
    seed(db, content)
    players.create_player(db, "ash", SYSTEM)
    players.create_player(db, "bo", SYSTEM)
    yield db
    db.close()


def make_character(
    conn: sqlite3.Connection,
    *,
    player_id: int = 1,
    origin: str = "street-born",
    knacks: tuple[str, str] = ("rooftop-runner", "back-alley-patch"),
    location: str = "tarp-row",
    online: bool = True,
) -> Character:
    sheet = new_sheet(STATS, knacks)
    char = characters.create_character(
        conn, player_id, "Mira", origin, "Nana Priya", sheet, SYSTEM, location_id=location
    )
    return characters.set_online(conn, char.id, online, SYSTEM) if online else char


@pytest.fixture
def mira(conn: sqlite3.Connection) -> Character:
    return make_character(conn)


def context_for(
    conn: sqlite3.Connection, content: Content, char: Character, *dice: int
) -> TurnContext:
    location = char.location_id or "tarp-row"
    scene = scenes.open_scene(conn, "market", SYSTEM, location_id=location)
    scenes.join_scene(conn, scene.id, char.id, SYSTEM)
    return TurnContext(
        conn, content, SeqRng(*dice), char.id, char.player_id, scene.id, now=NOON_TUESDAY
    )


@pytest.fixture
def ctx_factory(conn: sqlite3.Connection, content: Content) -> Callable[..., TurnContext]:
    def build(char: Character, *dice: int) -> TurnContext:
        return context_for(conn, content, char, *dice)

    return build


def next_turn(ctx: TurnContext) -> TurnContext:
    """The player's next action in the same scene: a fresh turn, allowed its own roll."""
    ctx.roll_ids.clear()
    ctx.changes.clear()
    ctx.encounters = 0
    ctx.moved_on.clear()
    ctx.spoken = None
    return ctx
