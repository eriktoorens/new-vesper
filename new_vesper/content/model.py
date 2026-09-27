"""Typed content records and strict parsing from JSON."""

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


@dataclass(frozen=True)
class OriginDef:
    id: str
    name: str
    trait: str
    tags: frozenset[str]


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


@dataclass(frozen=True)
class LocationDef:
    id: str
    region_id: str
    name: str
    is_haven: bool
    tags: frozenset[str]
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


def parse_origin(raw: object) -> OriginDef:
    r = Reader(raw, "origin", {"id", "name", "trait", "tags"})
    return OriginDef(r.slug("id"), r.text("name", 80), r.text("trait", 300), r.slugs("tags"))


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
    r = Reader(raw, "region", {"id", "name", "starting_light", "description"})
    return RegionDef(
        r.slug("id"),
        r.text("name", 80),
        r.integer("starting_light", LIGHT_MIN, LIGHT_MAX),
        r.text("description", 1000),
    )


def parse_location(raw: object, region_id: str) -> LocationDef:
    r = Reader(raw, "location", {"id", "name", "is_haven", "tags", "description"})
    return LocationDef(
        r.slug("id"),
        region_id,
        r.text("name", 80),
        r.boolean("is_haven"),
        r.slugs("tags"),
        r.text("description", 1000),
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
    r = Reader(raw, "npc", fields | {"tags"})
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
