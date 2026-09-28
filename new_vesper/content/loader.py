"""Load every content file into one validated, read-only registry."""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any

from new_vesper.content.model import (
    COMMON_TONGUE,
    CalendarDef,
    ClockDef,
    ContentError,
    GodDef,
    KnackDef,
    LanguageDef,
    LocationDef,
    LootTable,
    NpcDef,
    OriginDef,
    Reader,
    RegionDef,
    Spread,
    parse_calendar,
    parse_clock,
    parse_god,
    parse_knack,
    parse_language,
    parse_location,
    parse_loot_table,
    parse_npc,
    parse_origin,
    parse_region,
)

UNDERSIDE_ENTRANCE_TAG = "underside-entrance"
SHRINE_TAG = "shrine"


@dataclass(frozen=True)
class Content:
    origins: Mapping[str, OriginDef]
    knacks: Mapping[str, KnackDef]
    regions: Mapping[str, RegionDef]
    locations: Mapping[str, LocationDef]
    gods: Mapping[str, GodDef]
    npcs: Mapping[str, NpcDef]
    loot_tables: Mapping[str, LootTable]
    clocks: Mapping[str, ClockDef]
    languages: Mapping[str, LanguageDef]
    calendar: CalendarDef | None

    def npcs_at(self, location_id: str) -> list[NpcDef]:
        return [npc for npc in self.npcs.values() if npc.location == location_id]

    def locations_in(self, region_id: str) -> list[LocationDef]:
        return [loc for loc in self.locations.values() if loc.region_id == region_id]

    def underside_entrance(self, region_id: str) -> LocationDef | None:
        for location in self.locations_in(region_id):
            if UNDERSIDE_ENTRANCE_TAG in location.tags:
                return location
        return None

    def shrine_god(self, location_id: str) -> GodDef | None:
        return next((g for g in self.gods.values() if g.shrine == location_id), None)


def _index[T](items: Iterable[T], what: str) -> Mapping[str, T]:
    index: dict[str, T] = {}
    for item in items:
        key = item.id  # type: ignore[attr-defined]
        if key in index:
            raise ContentError(f"duplicate {what} id {key!r}")
        index[key] = item
    return MappingProxyType(index)


def _check_languages(content: Content) -> None:
    if content.languages and COMMON_TONGUE not in content.languages:
        raise ContentError(f"the common tongue {COMMON_TONGUE!r} must be defined")
    for origin in content.origins.values():
        for lang in (origin.language, *origin.language_choices):
            if lang is not None and lang not in content.languages:
                raise ContentError(f"origin {origin.id!r} names unknown language {lang!r}")
    for region in content.regions.values():
        if region.languages.get(COMMON_TONGUE) is not Spread.EVERYONE:
            raise ContentError(f"region {region.id!r}: everyone speaks {COMMON_TONGUE}")
    for place in (*content.regions.values(), *content.locations.values()):
        for lang in place.languages:
            if lang not in content.languages:
                raise ContentError(f"{place.id!r} lists unknown language {lang!r}")
    for npc in content.npcs.values():
        for lang in npc.languages:
            if lang not in content.languages:
                raise ContentError(f"npc {npc.id!r} speaks unknown language {lang!r}")
        if len(set(npc.languages)) != len(npc.languages):
            raise ContentError(f"npc {npc.id!r} lists a language twice")


def _check_map(content: Content) -> None:
    for region in content.regions.values():
        drawn = "\n".join(region.map)
        places = {loc.id for loc in content.locations_in(region.id)}
        if set(region.map_marks.values()) != places or len(region.map_marks) != len(places):
            raise ContentError(f"region {region.id!r}: every location needs exactly one map mark")
        for mark in region.map_marks:
            if drawn.count(f"[{mark}]") != 1:
                raise ContentError(
                    f"region {region.id!r}: mark [{mark}] must appear once on the map"
                )


def _check_schedules(content: Content) -> None:
    for npc in content.npcs.values():
        for other in npc.attitudes:
            if other not in content.npcs or other == npc.id:
                raise ContentError(f"npc {npc.id!r} has an attitude toward unknown {other!r}")
        for blocks in npc.schedule.values():
            for block in blocks:
                if block.location is not None and block.location not in content.locations:
                    raise ContentError(
                        f"npc {npc.id!r} is scheduled at unknown place {block.location!r}"
                    )


def _check_seasons(content: Content) -> None:
    if content.calendar is None:
        return
    for region in content.regions.values():
        if set(region.weather.seasons) != set(content.calendar.seasons):
            raise ContentError(f"region {region.id!r}: needs a weather table for every season")


def _check_references(content: Content) -> None:
    _check_seasons(content)
    _check_schedules(content)
    _check_languages(content)
    _check_map(content)
    for npc in content.npcs.values():
        if npc.location not in content.locations:
            raise ContentError(f"npc {npc.id!r} is at unknown location {npc.location!r}")
    for god in content.gods.values():
        shrine = content.locations.get(god.shrine)
        if shrine is None:
            raise ContentError(f"god {god.id!r} has unknown shrine {god.shrine!r}")
        if SHRINE_TAG not in shrine.tags or not shrine.is_haven:
            raise ContentError(f"shrine {shrine.id!r} must be tagged shrine and be a haven")
    for location in content.locations.values():
        if SHRINE_TAG in location.tags and not location.is_haven:
            raise ContentError(f"shrine {location.id!r} must be a haven")
    # look(entity) resolves an id to one thing, so these ids share a namespace.
    entities = [*content.locations, *content.npcs, *content.gods, *content.regions, *content.clocks]
    clashes = sorted({e for e in entities if entities.count(e) > 1})
    if clashes:
        raise ContentError(
            f"ids must be unique across regions, locations, npcs and gods: {clashes}"
        )


def load_documents(documents: Iterable[Mapping[str, Any]]) -> Content:
    """Build a registry from parsed JSON documents. Each top-level key is a section."""
    sections: dict[str, list[Any]] = {}
    locations: list[LocationDef] = []
    regions: list[RegionDef] = []
    clocks: list[ClockDef] = []
    calendar: CalendarDef | None = None
    allowed = {
        "origins",
        "knacks",
        "region",
        "locations",
        "gods",
        "npcs",
        "loot_tables",
        "clocks",
        "languages",
        "calendar",
    }
    for doc in documents:
        reader = Reader(doc, "content file", set(), allowed)
        if ("locations" in doc or "clocks" in doc) and "region" not in doc:
            raise ContentError("locations and clocks must sit in a file with their region")
        if "region" in doc:
            region = parse_region(doc["region"])
            regions.append(region)
            locations += [parse_location(raw, region.id) for raw in reader.items("locations")]
            if "clocks" in doc:
                clocks += [parse_clock(raw, region.id) for raw in reader.items("clocks")]
        if "calendar" in doc:
            if calendar is not None:
                raise ContentError("only one calendar")
            calendar = parse_calendar(doc["calendar"])
        for key in allowed - {"region", "locations", "clocks", "calendar"}:
            if key in doc:
                sections.setdefault(key, []).extend(reader.items(key))
    content = Content(
        origins=_index(map(parse_origin, sections.get("origins", [])), "origin"),
        knacks=_index(map(parse_knack, sections.get("knacks", [])), "knack"),
        regions=_index(regions, "region"),
        locations=_index(locations, "location"),
        gods=_index(map(parse_god, sections.get("gods", [])), "god"),
        npcs=_index(map(parse_npc, sections.get("npcs", [])), "npc"),
        loot_tables=_index(map(parse_loot_table, sections.get("loot_tables", [])), "loot table"),
        clocks=_index(clocks, "clock"),
        languages=_index(map(parse_language, sections.get("languages", [])), "language"),
        calendar=calendar,
    )
    _check_references(content)
    return content


def load_content(directory: Path | None = None) -> Content:
    """Load every ``*.json`` file in the packaged data directory (or ``directory``)."""
    root = directory if directory is not None else resources.files("new_vesper.content") / "data"
    files = sorted((p for p in root.iterdir() if p.name.endswith(".json")), key=lambda p: p.name)
    documents = []
    for path in files:
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise ContentError(f"{path.name}: invalid JSON: {exc}") from exc
    return load_documents(documents)
