"""The shipped content: what the build order asks for, and the setting guardrails."""

import re
from itertools import pairwise

import pytest

from new_vesper.content.loader import SHRINE_TAG, UNDERSIDE_ENTRANCE_TAG, Content, load_content
from new_vesper.rules.character import create_character
from new_vesper.rules.stats import STARTING_ARRAY, Stat


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


def test_market_district_shape(content: Content) -> None:
    assert set(content.regions) == {"market"}
    places = content.locations_in("market")
    entrances = [loc for loc in places if UNDERSIDE_ENTRANCE_TAG in loc.tags]
    assert [e.id for e in entrances] == ["drowned-station"]
    assert 4 <= len(places) - len(entrances) <= 5
    assert 4 <= len(content.npcs) <= 8
    assert len(content.gods) == 1
    assert len(content.loot_tables) == 1
    assert 7 <= len(content.knacks) <= 9


def test_three_four_segment_clocks(content: Content) -> None:
    assert len(content.clocks) == 3
    assert {c.segments for c in content.clocks.values()} == {4}
    assert {c.region_id for c in content.clocks.values()} == {"market"}


def test_lookups(content: Content) -> None:
    entrance = content.underside_entrance("market")
    assert entrance is not None and entrance.id == "drowned-station"
    god = content.shrine_god("umbrella-shrine")
    assert god is not None and god.id == "paru-of-lost-umbrellas"
    assert content.shrine_god("tarp-row") is None


def test_god_has_a_haven_shrine(content: Content) -> None:
    [god] = content.gods.values()
    shrine = content.locations[god.shrine]
    assert SHRINE_TAG in shrine.tags
    assert shrine.is_haven


def test_there_is_somewhere_to_log_off(content: Content) -> None:
    havens = [loc for loc in content.locations_in("market") if loc.is_haven]
    assert {"lodging", "shrine"} <= {tag for loc in havens for tag in loc.tags}


def test_the_underside_entrance_is_not_safe(content: Content) -> None:
    assert not content.locations["drowned-station"].is_haven


def test_every_npc_has_pronouns_and_a_place(content: Content) -> None:
    for npc in content.npcs.values():
        assert npc.pronouns
        assert npc.location in content.locations
    assert all(content.npcs_at(loc) for loc in ("drowned-station", "hundred-hooks"))


def test_origins_match_the_design_doc(content: Content) -> None:
    assert set(content.origins) == {
        "street-born",
        "made-person",
        "enclave-raised",
        "underside-born",
        "awakened-animal",
    }
    assert {"no-hands", "overlooked", "animal-speech"} <= content.origins["awakened-animal"].tags


def test_starter_knacks_respect_the_balance_budget(content: Content) -> None:
    for knack in content.knacks.values():
        assert knack.roll_bonus <= 1
        if knack.roll_bonus:
            assert knack.limit is not None
    assert {k.stat for k in content.knacks.values()} == set(Stat)


def test_lock_picking_is_tagged_for_hands(content: Content) -> None:
    assert "needs-hands" in content.knacks["quick-fingers"].tags


def test_tech_magic_knack_uses_wire(content: Content) -> None:
    knack = content.knacks["prayer-net-tap"]
    assert knack.stat is Stat.WIRE
    assert "tech-magic" in knack.tags


def test_any_two_starter_knacks_make_a_character(content: Content) -> None:
    stats = dict(zip(Stat, STARTING_ARRAY, strict=True))
    ids = list(content.knacks)
    for a, b in pairwise(ids):
        assert create_character(stats, (a, b)).knacks == (a, b)


# Gods and figures from living religions must not appear; the setting's gods
# are invented. Not exhaustive: a tripwire, not a substitute for review.
LIVING_RELIGION_NAMES = [
    "allah",
    "yahweh",
    "jehovah",
    "jesus",
    "christ",
    "mary",
    "buddha",
    "bodhisattva",
    "guanyin",
    "kannon",
    "vishnu",
    "shiva",
    "krishna",
    "ganesh",
    "ganesha",
    "kali",
    "lakshmi",
    "durga",
    "hanuman",
    "brahma",
    "amaterasu",
    "inari",
    "kami",
    "orisha",
    "oshun",
    "yemoja",
    "shango",
    "ogun",
    "obatala",
    "loa",
    "lwa",
    "papa legba",
    "odin",
    "thor",
    "freya",
    "waheguru",
    "ahura mazda",
    "jah",
    "saint",
]


def _all_text(content: Content) -> str:
    parts: list[str] = []
    for section in (
        content.gods,
        content.npcs,
        content.locations,
        content.regions,
        content.knacks,
        content.origins,
        content.loot_tables,
    ):
        parts += [repr(item) for item in section.values()]
    return " ".join(parts).lower()


@pytest.mark.parametrize("name", LIVING_RELIGION_NAMES)
def test_no_gods_from_living_religions(content: Content, name: str) -> None:
    assert not re.search(rf"\b{re.escape(name)}\b", _all_text(content))
