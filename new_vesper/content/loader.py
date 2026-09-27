"""Load every content file into one validated, read-only registry."""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any

from new_vesper.content.model import (
    ClockDef,
    ContentError,
    GodDef,
    KnackDef,
    LocationDef,
    LootTable,
    NpcDef,
    OriginDef,
    Reader,
    RegionDef,
    parse_clock,
    parse_god,
    parse_knack,
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


def _check_references(content: Content) -> None:
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
    allowed = {"origins", "knacks", "region", "locations", "gods", "npcs", "loot_tables", "clocks"}
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
        for key in allowed - {"region", "locations", "clocks"}:
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
