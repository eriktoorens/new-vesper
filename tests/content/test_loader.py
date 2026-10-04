"""The loader rejects malformed and inconsistent content."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from new_vesper.content.loader import load_content, load_documents
from new_vesper.content.model import ContentError, parse_language, parse_origin

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
    "languages": [
        {
            "id": "registry-standard",
            "name": "Registry Standard",
            "common": True,
            "description": "d",
        },
        {"id": "hush", "name": "Hush", "common": False, "description": "d"},
    ],
    "region": {
        "id": "r",
        "name": "R",
        "starting_light": 5,
        "description": "d",
        "map": ["  [1]  "],
        "map_marks": {"1": "shrine"},
        "languages": [{"language": "registry-standard", "spread": "everyone"}],
        "culture": "c",
        "weather": {
            "states": [{"id": "rain", "name": "Rain", "description": "d"}],
            "seasons": {"always": {"start": "rain", "transitions": {"rain": {"rain": 1}}}},
        },
    },
    "locations": [
        {
            "id": "shrine",
            "name": "S",
            "is_haven": True,
            "tags": ["shrine"],
            "description": "d",
            "art": ["  /\\  "],
            "languages": [{"language": "hush", "spread": "some"}],
            "tide": None,
        },
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
            "age": "old",
            "appearance": "a",
            "languages": ["registry-standard"],
            "portrait": [" :) "],
            "schedule": {
                "default": [{"from": "00:00", "to": "24:00", "location": "shrine", "activity": "a"}]
            },
            "goal": {"text": "g", "stages": ["s"], "days_per_stage": 2},
            "traits": ["t"],
            "speech": ["s"],
            "sample_line": "l",
            "attitude_to_strangers": {"trust": 0, "fondness": 0, "fear": 0},
            "attitudes": {},
            "moods": {"usual": ["calm", "busy"], "foul_weather": ["damp"], "goal_news": ["glad"]},
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
        _region(npcs__0__languages=["klingon"]),
        _region(npcs__0__languages=[]),
        _region(npcs__0__portrait=["\tmisaligned"]),
        _region(npcs__0__portrait=["x" * 61]),
        _region(locations__0__art=["caf\u00e9"]),
        _region(region__x__map_marks={"1": "nowhere"}),
        _region(region__x__map=["no marks at all"]),
        _region(region__x__map=["[1] and again [1]"]),
        _region(region__x__languages=[{"language": "hush", "spread": "everyone"}]),
        _region(region__x__languages=[{"language": "registry-standard", "spread": "all"}]),
        _region(locations__0__languages=[{"language": "martian", "spread": "few"}]),
        _region(region__x__culture=""),
        _region(npcs__0__attitudes={"n": {"trust": 0, "fondness": 0, "fear": 0, "why": "w"}}),
        _region(npcs__0__attitudes={"ghost": {"trust": 0, "fondness": 0, "fear": 0, "why": "w"}}),
        _region(npcs__0__attitude_to_strangers={"trust": 4, "fondness": 0, "fear": 0}),
        _region(npcs__0__traits=[]),
        _region(npcs__0__moods={"usual": ["calm"], "foul_weather": ["damp"], "goal_news": ["g"]}),
        _region(npcs__0__moods={"usual": ["a", "b"], "foul_weather": [], "goal_news": ["g"]}),
        _region(
            npcs__0__moods={"usual": ["a", "x" * 61], "foul_weather": ["d"], "goal_news": ["g"]}
        ),
        _region(npcs__0__moods={"usual": ["a", "b"], "foul_weather": ["d"]}),
        _region(
            region__x__weather={
                "states": [{"id": "rain", "name": "R", "description": "d"}],
                "seasons": {"s": {"start": "rain", "transitions": {"rain": {"hail": 1}}}},
            }
        ),
        _region(
            region__x__weather={
                "states": [{"id": "rain", "name": "R", "description": "d"}],
                "seasons": {"s": {"start": "sun", "transitions": {"rain": {"rain": 1}}}},
            }
        ),
        _region(locations__0__tide={"closed_when": ["moonrise"], "notes": {}, "min_rung": []}),
        _region(
            locations__0__tide={
                "closed_when": [],
                "notes": {},
                "min_rung": [{"when": "high", "stats": ["luck"], "rung": "hard", "why": "w"}],
            }
        ),
        _region(
            npcs__0__schedule={
                "default": [{"from": "00:00", "to": "12:00", "location": "shrine", "activity": "a"}]
            }
        ),
        _region(
            npcs__0__schedule={
                "default": [
                    {"from": "00:00", "to": "13:00", "location": "shrine", "activity": "a"},
                    {"from": "12:00", "to": "24:00", "location": "shrine", "activity": "b"},
                ]
            }
        ),
        _region(
            npcs__0__schedule={
                "funday": [{"from": "00:00", "to": "24:00", "location": "shrine", "activity": "a"}]
            }
        ),
        _region(
            npcs__0__schedule={
                "default": [{"from": "00:00", "to": "24:00", "location": "narnia", "activity": "a"}]
            }
        ),
        _region(
            npcs__0__schedule={
                "default": [{"from": "0:00", "to": "24:00", "location": "shrine", "activity": "a"}]
            }
        ),
        _region(npcs__0__goal={"text": "g", "stages": [], "days_per_stage": 2}),
        {"clocks": []},  # clocks without a region
        {**_region(), "clocks": [{"id": "c", "name": "C", "segments": 6, "description": "d"}]},
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


@pytest.mark.parametrize(
    "sounds",
    [
        ["ack", "nak", "sync"],  # too few to sound like anything
        ["ack", "nak", "sync", "much-too-long"],
        ["ack", "nak", "sync", "ñak"],
        ["ack", "nak", "sync", " "],
        "ack nak",
    ],
)
def test_bad_language_sounds_rejected(sounds: Any) -> None:
    raw = {"id": "hush", "name": "Hush", "common": False, "description": "x", "sounds": sounds}
    with pytest.raises(ContentError):
        parse_language(raw)


def test_language_sounds_are_optional() -> None:
    raw = {"id": "hush", "name": "Hush", "common": False, "description": "x"}
    assert parse_language(raw).sounds == ()
    assert parse_language(raw | {"sounds": ["a", "b", "c", "d"]}).sounds == ("a", "b", "c", "d")


@pytest.mark.parametrize(
    "edit",
    [
        {"climate": "cozy"},
        {"provisions": {"snacks": {"what": "x", "price": 1}}},
        {"provisions": {"food": {"what": "x", "price": -1}}},
        {"provisions": {"food": {"what": "x", "price": True}}},
        {"provisions": {"food": {"what": "", "price": 1}}},
        {"provisions": {"food": {"what": "x"}}},
        {"provisions": []},
    ],
)
def test_bad_climate_and_provisions_rejected(edit: dict[str, Any]) -> None:
    doc = _region()
    doc["locations"][0] |= edit
    with pytest.raises(ContentError):
        load_documents([doc])


def test_climate_and_provisions_load() -> None:
    doc = _region()
    doc["locations"][0] |= {
        "climate": "sheltered",
        "provisions": {"drink": {"what": "rainwater", "price": 0}},
    }
    place = load_documents([doc]).locations["shrine"]
    assert place.climate.value == "sheltered"
    assert [(n.value, p.price) for n, p in place.provisions.items()] == [("thirst", 0)]
    assert load_documents([_region()]).locations["shrine"].climate.value == "exposed"


@pytest.mark.parametrize("exposure", ["warm", "none", 1])
def test_bad_weather_exposure_rejected(exposure: Any) -> None:
    doc = _region()
    doc["region"]["weather"]["states"][0]["exposure"] = exposure
    with pytest.raises(ContentError):
        load_documents([doc])


ORIGIN = {
    "id": "o",
    "name": "O",
    "trait": "t",
    "tags": [],
    "language": "registry-standard",
    "language_choices": [],
}


@pytest.mark.parametrize("needs", [["boredom"], ["hunger", "hunger"], "hunger", [1]])
def test_bad_origin_needs_rejected(needs: Any) -> None:
    with pytest.raises(ContentError):
        parse_origin(ORIGIN | {"needs": needs})


def test_origin_needs_default_to_all() -> None:
    assert len(parse_origin(ORIGIN).needs) == 5
    assert parse_origin(ORIGIN | {"needs": []}).needs == frozenset()
