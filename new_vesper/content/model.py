"""Typed content records and strict parsing from JSON."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from new_vesper.rules.character import validate_id
from new_vesper.rules.errors import RulesError, require_range
from new_vesper.rules.light import LIGHT_MAX, LIGHT_MIN
from new_vesper.rules.resolver import MAX_ROLL_BONUS
from new_vesper.rules.stats import Stat, parse_stat


class ContentError(ValueError):
    """A content file is malformed or inconsistent."""


class LimitPeriod(StrEnum):
    SCENE = "scene"
    DAY = "day"


class GodKind(StrEnum):
    OLD = "old"
    CORPORATE = "corporate"


@dataclass(frozen=True)
class UseLimit:
    uses: int
    per: LimitPeriod

    def describe(self) -> str:
        return f"{self.uses} per {self.per}"


# Everyone in the city speaks Registry Standard.
COMMON_TONGUE = "registry-standard"
# ASCII art limits: small enough for any terminal.
ART_MAX_WIDTH = 60
ART_MAX_LINES = 10
MAP_MAX_WIDTH = 72
MAP_MAX_LINES = 24


class Spread(StrEnum):
    """How widely a language is spoken in a neighborhood."""

    EVERYONE = "everyone"
    MOST = "most"
    MANY = "many"
    SOME = "some"
    FEW = "few"


MINUTES_PER_DAY = 1440
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class ScheduleBlock:
    start: int  # minutes after city midnight
    end: int  # may be less than start: the block runs past midnight
    location: str | None  # None: away from the district
    activity: str

    def covers(self, minute: int) -> bool:
        if self.start < self.end:
            return self.start <= minute < self.end
        return minute >= self.start or minute < self.end

    def minutes(self) -> set[int]:
        return {m for m in range(MINUTES_PER_DAY) if self.covers(m)}


@dataclass(frozen=True)
class NpcGoal:
    text: str
    stages: tuple[str, ...]
    days_per_stage: int


@dataclass(frozen=True)
class WeatherState:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class WeatherDef:
    start: str
    states: Mapping[str, WeatherState]
    transitions: Mapping[str, Mapping[str, int]]


@dataclass(frozen=True)
class LanguageDef:
    id: str
    name: str
    common: bool  # recognizable by name even to those who don't speak it
    description: str


@dataclass(frozen=True)
class OriginDef:
    id: str
    name: str
    trait: str
    tags: frozenset[str]
    # The origin's language: fixed, or one chosen from these at creation.
    language: str | None
    language_choices: tuple[str, ...]


@dataclass(frozen=True)
class KnackDef:
    id: str
    name: str
    stat: Stat
    trigger: str
    clean_effect: str
    cost_effect: str
    roll_bonus: int
    limit: UseLimit | None
    tags: frozenset[str]


@dataclass(frozen=True)
class RegionDef:
    id: str
    name: str
    starting_light: int
    description: str
    map: tuple[str, ...]
    # "1" -> location id: the map shows each location as [1], [2]...
    map_marks: Mapping[str, str]
    # Who speaks what here, and the neighborhood's cultural flavor.
    languages: Mapping[str, Spread]
    culture: str
    weather: WeatherDef


@dataclass(frozen=True)
class LocationDef:
    id: str
    region_id: str
    name: str
    is_haven: bool
    tags: frozenset[str]
    description: str
    art: tuple[str, ...]
    # Languages more common here than in the district as a whole.
    languages: Mapping[str, Spread]


@dataclass(frozen=True)
class ClockDef:
    id: str
    region_id: str
    name: str
    segments: int
    description: str


@dataclass(frozen=True)
class GodDef:
    id: str
    name: str
    kind: GodKind
    shrine: str
    domain: str
    description: str
    wants: str
    grievance: str
    collects: tuple[str, ...]


@dataclass(frozen=True)
class NpcDef:
    id: str
    name: str
    pronouns: str
    location: str
    role: str
    description: str
    wants: str
    voice: str
    tags: frozenset[str]
    age: str
    appearance: str
    languages: tuple[str, ...]
    portrait: tuple[str, ...]
    # "default" plus any weekdays that differ.
    schedule: Mapping[str, tuple[ScheduleBlock, ...]]
    goal: NpcGoal


@dataclass(frozen=True)
class LootEntry:
    kind: str
    name: str
    weight: int


@dataclass(frozen=True)
class LootTable:
    id: str
    name: str
    entries: tuple[LootEntry, ...]

    @property
    def total_weight(self) -> int:
        return sum(entry.weight for entry in self.entries)


class Reader:
    """Reads one JSON object, rejecting missing, unknown and mistyped fields."""

    def __init__(
        self, raw: object, where: str, required: set[str], optional: set[str] = frozenset()
    ):
        if not isinstance(raw, dict):
            raise ContentError(f"{where}: expected an object")
        missing = required - raw.keys()
        unknown = raw.keys() - required - optional
        if missing:
            raise ContentError(f"{where}: missing {sorted(missing)}")
        if unknown:
            raise ContentError(f"{where}: unknown fields {sorted(unknown)}")
        self.raw: dict[str, Any] = raw
        self.where = where

    def text(self, key: str, max_length: int = 600) -> str:
        value = self.raw[key]
        if not isinstance(value, str) or not value.strip() or len(value) > max_length:
            raise ContentError(f"{self.where}.{key}: expected text of 1-{max_length} characters")
        return value

    def slug(self, key: str) -> str:
        return self._slug(self.raw[key], f"{self.where}.{key}")

    def slugs(self, key: str) -> frozenset[str]:
        values = self.raw[key]
        if not isinstance(values, list):
            raise ContentError(f"{self.where}.{key}: expected a list")
        return frozenset(self._slug(v, f"{self.where}.{key}") for v in values)

    def texts(self, key: str) -> tuple[str, ...]:
        values = self.raw[key]
        if not isinstance(values, list) or not all(isinstance(v, str) and v for v in values):
            raise ContentError(f"{self.where}.{key}: expected a list of text")
        return tuple(values)

    def art(
        self, key: str, max_width: int = ART_MAX_WIDTH, max_lines: int = ART_MAX_LINES
    ) -> tuple[str, ...]:
        """Plain printable ASCII lines, so art lines up in any terminal."""
        lines = self.raw[key]
        where = f"{self.where}.{key}"
        if not isinstance(lines, list) or not 1 <= len(lines) <= max_lines:
            raise ContentError(f"{where}: expected 1-{max_lines} lines")
        for line in lines:
            if not isinstance(line, str) or len(line) > max_width:
                raise ContentError(f"{where}: lines must be text of at most {max_width} columns")
            if any(not (32 <= ord(c) < 127) for c in line):
                raise ContentError(f"{where}: art must be plain printable ASCII")
        return tuple(line.rstrip() for line in lines)

    def boolean(self, key: str) -> bool:
        value = self.raw[key]
        if not isinstance(value, bool):
            raise ContentError(f"{self.where}.{key}: expected true or false")
        return value

    def integer(self, key: str, low: int, high: int) -> int:
        try:
            return require_range(self.raw[key], f"{self.where}.{key}", low, high)
        except RulesError as exc:
            raise ContentError(str(exc)) from exc

    def items(self, key: str) -> list[Any]:
        values = self.raw[key]
        if not isinstance(values, list):
            raise ContentError(f"{self.where}.{key}: expected a list")
        return values

    @staticmethod
    def _slug(value: object, where: str) -> str:
        try:
            return validate_id(value, where)
        except RulesError as exc:
            raise ContentError(f"{where}: {exc}") from exc


def _spread_map(raw: object, where: str) -> Mapping[str, Spread]:
    """A list of {language, spread} entries: how widely each language is spoken."""
    if not isinstance(raw, list):
        raise ContentError(f"{where}: expected a list of {{language, spread}}")
    spread: dict[str, Spread] = {}
    for entry in raw:
        e = Reader(entry, where, {"language", "spread"})
        language = e.slug("language")
        if e.raw["spread"] not in {s.value for s in Spread}:
            raise ContentError(f"{where}: spread must be one of {[s.value for s in Spread]}")
        if language in spread:
            raise ContentError(f"{where}: {language!r} listed twice")
        spread[language] = Spread(e.raw["spread"])
    return spread


def _minute(value: object, where: str, *, end: bool) -> int:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise ContentError(f"{where}: times are HH:MM")
    try:
        hours, minutes = int(value[:2]), int(value[3:])
    except ValueError:
        raise ContentError(f"{where}: times are HH:MM") from None
    total = hours * 60 + minutes
    limit = MINUTES_PER_DAY if end else MINUTES_PER_DAY - 1
    if minutes >= 60 or not 0 <= total <= limit:
        raise ContentError(f"{where}: {value!r} is not a time of day")
    return total


def _parse_schedule(raw: object, where: str) -> Mapping[str, tuple[ScheduleBlock, ...]]:
    """Each day's blocks must cover all 24 hours exactly once."""
    if not isinstance(raw, dict) or "default" not in raw:
        raise ContentError(f"{where}: needs a default day")
    days: dict[str, tuple[ScheduleBlock, ...]] = {}
    for day, blocks in raw.items():
        if day != "default" and day not in WEEKDAYS:
            raise ContentError(f"{where}: {day!r} is not a weekday")
        if not isinstance(blocks, list) or not blocks:
            raise ContentError(f"{where}.{day}: expected a list of blocks")
        parsed = []
        for block in blocks:
            b = Reader(block, f"{where}.{day}", {"from", "to", "location", "activity"})
            start = _minute(b.raw["from"], f"{where}.{day}", end=False)
            stop = _minute(b.raw["to"], f"{where}.{day}", end=True) % MINUTES_PER_DAY
            location = None if b.raw["location"] is None else b.slug("location")
            parsed.append(ScheduleBlock(start, stop, location, b.text("activity", 200)))
        covered: list[int] = []
        for block in parsed:
            covered += sorted(block.minutes())
        if len(covered) != MINUTES_PER_DAY or len(set(covered)) != MINUTES_PER_DAY:
            raise ContentError(f"{where}.{day}: blocks must cover the whole day exactly once")
        days[day] = tuple(parsed)
    return days


def _parse_goal(raw: object, where: str) -> NpcGoal:
    r = Reader(raw, where, {"text", "stages", "days_per_stage"})
    stages = r.texts("stages")
    if not stages:
        raise ContentError(f"{where}: needs at least one stage")
    return NpcGoal(r.text("text", 300), stages, r.integer("days_per_stage", 1, 30))


def _parse_weather(raw: object) -> WeatherDef:
    r = Reader(raw, "region.weather", {"start", "states", "transitions"})
    states: dict[str, WeatherState] = {}
    for entry in r.items("states"):
        s = Reader(entry, "region.weather.states", {"id", "name", "description"})
        state = WeatherState(s.slug("id"), s.text("name", 40), s.text("description", 300))
        if state.id in states:
            raise ContentError(f"weather state {state.id!r} listed twice")
        states[state.id] = state
    transitions = r.raw["transitions"]
    if not isinstance(transitions, dict) or set(transitions) != set(states):
        raise ContentError("region.weather.transitions: one entry per weather state")
    table: dict[str, dict[str, int]] = {}
    for state, options in transitions.items():
        if not isinstance(options, dict) or not options:
            raise ContentError(f"weather {state!r}: needs weighted next states")
        for target, weight in options.items():
            if target not in states:
                raise ContentError(f"weather {state!r} moves to unknown {target!r}")
            if isinstance(weight, bool) or not isinstance(weight, int) or not 1 <= weight <= 100:
                raise ContentError(f"weather {state!r}: weights are integers 1-100")
        table[state] = dict(options)
    start = r.slug("start")
    if start not in states:
        raise ContentError(f"weather start {start!r} is not a state")
    return WeatherDef(start, states, table)


def parse_language(raw: object) -> LanguageDef:
    r = Reader(raw, "language", {"id", "name", "common", "description"})
    return LanguageDef(
        r.slug("id"), r.text("name", 40), r.boolean("common"), r.text("description", 300)
    )


def parse_origin(raw: object) -> OriginDef:
    r = Reader(raw, "origin", {"id", "name", "trait", "tags", "language", "language_choices"})
    language = None if r.raw["language"] is None else r.slug("language")
    choices = tuple(sorted(r.slugs("language_choices")))
    if (language is None) == (not choices):
        raise ContentError(
            f"origin {r.raw['id']!r}: give either a language or language_choices, not both"
        )
    return OriginDef(
        r.slug("id"), r.text("name", 80), r.text("trait", 300), r.slugs("tags"), language, choices
    )


def parse_knack(raw: object) -> KnackDef:
    fields = {"id", "name", "stat", "trigger", "clean_effect", "cost_effect", "roll_bonus", "limit"}
    r = Reader(raw, "knack", fields | {"tags"})
    where = f"knack {r.raw.get('id')!r}"
    try:
        stat = parse_stat(r.raw["stat"])
    except RulesError as exc:
        raise ContentError(f"{where}: {exc}") from exc
    roll_bonus = r.integer("roll_bonus", 0, MAX_ROLL_BONUS)
    limit = None
    if r.raw["limit"] is not None:
        lr = Reader(r.raw["limit"], f"{where}.limit", {"uses", "per"})
        if lr.raw["per"] not in {p.value for p in LimitPeriod}:
            raise ContentError(f"{where}.limit.per: expected scene or day")
        limit = UseLimit(lr.integer("uses", 1, 3), LimitPeriod(lr.raw["per"]))
    # Balance budget: a knack that adds to the roll is strong and must be limited.
    if roll_bonus and limit is None:
        raise ContentError(f"{where}: a knack with a roll bonus needs a use limit")
    return KnackDef(
        id=r.slug("id"),
        name=r.text("name", 80),
        stat=stat,
        trigger=r.text("trigger", 500),
        clean_effect=r.text("clean_effect", 500),
        cost_effect=r.text("cost_effect", 500),
        roll_bonus=roll_bonus,
        limit=limit,
        tags=r.slugs("tags"),
    )


def parse_region(raw: object) -> RegionDef:
    fields = {"id", "name", "starting_light", "description", "map", "map_marks", "languages"}
    r = Reader(raw, "region", fields | {"culture", "weather"})
    marks = r.raw["map_marks"]
    if not isinstance(marks, dict) or not marks:
        raise ContentError("region.map_marks: expected an object of mark -> location id")
    for mark in marks:
        if not (isinstance(mark, str) and mark.isdigit() and len(mark) == 1):
            raise ContentError("region.map_marks: marks are single digits 1-9")
    return RegionDef(
        r.slug("id"),
        r.text("name", 80),
        r.integer("starting_light", LIGHT_MIN, LIGHT_MAX),
        r.text("description", 1000),
        r.art("map", MAP_MAX_WIDTH, MAP_MAX_LINES),
        {mark: Reader._slug(loc, f"region.map_marks.{mark}") for mark, loc in marks.items()},
        _spread_map(r.raw["languages"], "region.languages"),
        r.text("culture", 1000),
        _parse_weather(r.raw["weather"]),
    )


def parse_location(raw: object, region_id: str) -> LocationDef:
    fields = {"id", "name", "is_haven", "tags", "description", "art", "languages"}
    r = Reader(raw, "location", fields)
    return LocationDef(
        r.slug("id"),
        region_id,
        r.text("name", 80),
        r.boolean("is_haven"),
        r.slugs("tags"),
        r.text("description", 1000),
        r.art("art"),
        _spread_map(r.raw["languages"], f"location {r.raw['id']!r} languages"),
    )


# Threat clocks have 4 segments (D6).
CLOCK_SEGMENTS = 4


def parse_clock(raw: object, region_id: str) -> ClockDef:
    r = Reader(raw, "clock", {"id", "name", "segments", "description"})
    return ClockDef(
        r.slug("id"),
        region_id,
        r.text("name", 80),
        r.integer("segments", CLOCK_SEGMENTS, CLOCK_SEGMENTS),
        r.text("description", 500),
    )


def parse_god(raw: object) -> GodDef:
    fields = {"id", "name", "kind", "shrine", "domain", "description", "wants", "grievance"}
    r = Reader(raw, "god", fields | {"collects"})
    if r.raw["kind"] not in {k.value for k in GodKind}:
        raise ContentError("god.kind: expected old or corporate")
    return GodDef(
        id=r.slug("id"),
        name=r.text("name", 80),
        kind=GodKind(r.raw["kind"]),
        shrine=r.slug("shrine"),
        domain=r.text("domain", 300),
        description=r.text("description", 1000),
        wants=r.text("wants", 300),
        grievance=r.text("grievance", 500),
        collects=r.texts("collects"),
    )


def parse_npc(raw: object) -> NpcDef:
    fields = {"id", "name", "pronouns", "location", "role", "description", "wants", "voice"}
    extra = {"tags", "age", "appearance", "languages", "portrait", "schedule", "goal"}
    r = Reader(raw, "npc", fields | extra)
    languages = r.raw["languages"]
    if not isinstance(languages, list) or not languages:
        raise ContentError(f"npc {r.raw['id']!r}: needs at least one language")
    return NpcDef(
        id=r.slug("id"),
        name=r.text("name", 80),
        pronouns=r.text("pronouns", 30),
        location=r.slug("location"),
        role=r.text("role", 120),
        description=r.text("description", 1000),
        wants=r.text("wants", 300),
        voice=r.text("voice", 300),
        tags=r.slugs("tags"),
        age=r.text("age", 60),
        appearance=r.text("appearance", 300),
        languages=tuple(Reader._slug(v, "npc.languages") for v in languages),
        portrait=r.art("portrait"),
        schedule=_parse_schedule(r.raw["schedule"], f"npc {r.raw['id']!r} schedule"),
        goal=_parse_goal(r.raw["goal"], f"npc {r.raw['id']!r} goal"),
    )


def parse_loot_table(raw: object) -> LootTable:
    r = Reader(raw, "loot table", {"id", "name", "entries"})
    entries = []
    for item in r.items("entries"):
        er = Reader(item, f"loot table {r.raw['id']!r} entry", {"kind", "name", "weight"})
        entries.append(
            LootEntry(er.slug("kind"), er.text("name", 80), er.integer("weight", 1, 100))
        )
    if not entries:
        raise ContentError(f"loot table {r.raw['id']!r}: needs at least one entry")
    kinds = [e.kind for e in entries]
    if len(set(kinds)) != len(kinds):
        raise ContentError(f"loot table {r.raw['id']!r}: duplicate item kind")
    return LootTable(r.slug("id"), r.text("name", 80), tuple(entries))
