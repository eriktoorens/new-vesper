"""The loader rejects malformed and inconsistent content."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from new_vesper.content.loader import load_content, load_documents
from new_vesper.content.model import ContentError

KNACK = {
    "id": "k",
    "name": "K",
    "stat": "wire",
    "trigger": "t",
    "clean_effect": "c",
    "cost_effect": "c",
    "roll_bonus": 0,
    "limit": None,
    "tags": [],
}
REGION_DOC: dict[str, Any] = {
    "region": {"id": "r", "name": "R", "starting_light": 5, "description": "d"},
    "locations": [
        {"id": "shrine", "name": "S", "is_haven": True, "tags": ["shrine"], "description": "d"},
    ],
    "gods": [
        {
            "id": "g",
            "name": "G",
            "kind": "old",
            "shrine": "shrine",
            "domain": "d",
            "description": "d",
            "wants": "w",
            "grievance": "g",
            "collects": [],
        }
    ],
    "npcs": [
        {
            "id": "n",
            "name": "N",
            "pronouns": "they/them",
            "location": "shrine",
            "role": "r",
            "description": "d",
            "wants": "w",
            "voice": "v",
            "tags": [],
        }
    ],
}


def _region(**edits: Any) -> dict[str, Any]:
    doc = copy.deepcopy(REGION_DOC)
    for path, value in edits.items():
        section, index, key = path.split("__")
        target = doc[section] if index == "x" else doc[section][int(index)]
        target[key] = value
    return doc


def test_minimal_documents_load() -> None:
    content = load_documents([{"knacks": [KNACK]}, _region()])
    assert set(content.knacks) == {"k"}
    assert content.npcs_at("shrine")[0].id == "n"


@pytest.mark.parametrize(
    "knack",
    [
        {**KNACK, "stat": "luck"},
        {**KNACK, "roll_bonus": 2},
        {**KNACK, "roll_bonus": 1},  # bonus without a use limit
        {**KNACK, "roll_bonus": 1, "limit": {"uses": 1, "per": "week"}},
        {**KNACK, "roll_bonus": 1, "limit": {"uses": 9, "per": "scene"}},
        {**KNACK, "roll_bonus": True},
        {**KNACK, "id": "Bad Id"},
        {**KNACK, "name": ""},
        {**KNACK, "clean_effect": "x" * 501},
        {**KNACK, "damage": 10},  # unknown field
        {k: v for k, v in KNACK.items() if k != "trigger"},
        {**KNACK, "tags": "magic"},
    ],
)
def test_bad_knacks_rejected(knack: dict[str, Any]) -> None:
    with pytest.raises(ContentError):
        load_documents([{"knacks": [knack]}])


@pytest.mark.parametrize(
    "doc",
    [
        _region(npcs__0__location="nowhere"),
        _region(gods__0__shrine="nowhere"),
        _region(locations__0__is_haven=False),
        _region(gods__0__kind="demigod"),
        _region(region__x__starting_light=11),
        _region(npcs__0__id="shrine"),  # clashes with a location id
        _region(npcs__0__pronouns=""),
        {"locations": REGION_DOC["locations"]},  # locations without a region
        {"monsters": []},
    ],
)
def test_inconsistent_region_rejected(doc: dict[str, Any]) -> None:
    with pytest.raises(ContentError):
        load_documents([doc])


def test_duplicate_ids_across_files_rejected() -> None:
    with pytest.raises(ContentError, match="duplicate"):
        load_documents([{"knacks": [KNACK]}, {"knacks": [KNACK]}])


@pytest.mark.parametrize(
    "entries",
    [
        [],
        [{"kind": "a", "name": "A", "weight": 0}],
        [{"kind": "a", "name": "A", "weight": 1}, {"kind": "a", "name": "B", "weight": 1}],
        [{"kind": "a", "name": "A", "weight": 1, "rarity": "legendary"}],
    ],
)
def test_bad_loot_tables_rejected(entries: list[Any]) -> None:
    table = {"id": "t", "name": "T", "entries": entries}
    with pytest.raises(ContentError):
        load_documents([{"loot_tables": [table]}])


def test_invalid_json_file_rejected(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not json")
    with pytest.raises(ContentError, match=r"broken\.json"):
        load_content(tmp_path)


def test_directory_loading(tmp_path: Path) -> None:
    (tmp_path / "knacks.json").write_text(json.dumps({"knacks": [KNACK]}))
    (tmp_path / "notes.txt").write_text("ignored")
    assert set(load_content(tmp_path).knacks) == {"k"}
