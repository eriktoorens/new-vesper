import random

from new_vesper.content.loader import load_content
from new_vesper.content.loot import roll_loot
from new_vesper.content.seed import seed
from new_vesper.rules.character import create_character as new_sheet
from new_vesper.rules.light import encroach
from new_vesper.rules.stats import STARTING_ARRAY, Stat
from new_vesper.state import characters, items, players, world
from new_vesper.state.db import open_database
from new_vesper.state.events import SYSTEM, list_events


def test_seed_then_play() -> None:
    conn = open_database()
    content = load_content()
    added = seed(conn, content)
    assert "region:market" in added
    assert len(added) == 10 + 5 + 8 + 1 + 8 + 3 + 19  # 19 authored NPC-to-NPC attitudes
    assert world.get_region(conn, "market").light == 6
    assert world.get_location(conn, "hundred-hooks").is_haven
    assert world.get_knack(conn, "rooftop-runner").limits == "1 per scene"

    player = players.create_player(conn, "ash", SYSTEM)
    sheet = new_sheet(
        dict(zip(Stat, STARTING_ARRAY, strict=True)), ("quick-fingers", "say-their-name")
    )
    cat = characters.create_character(
        conn,
        player.id,
        "Biscuit",
        "awakened-animal",
        "The noodle man",
        sheet,
        SYSTEM,
        location_id="tarp-row",
    )
    assert "no-hands" in cat.tags

    entry = roll_loot(content.loot_tables["market-stalls"], random.Random(3))
    item = items.create_item(conn, entry.kind, entry.name, SYSTEM, character_id=cat.id)
    assert item.kind in {e.kind for e in content.loot_tables["market-stalls"].entries}


def test_seed_is_idempotent_and_keeps_light() -> None:
    conn = open_database()
    content = load_content()
    seed(conn, content)
    world.apply_light_change(conn, "market", encroach(6), SYSTEM, "neglect")
    events_before = len(list_events(conn, limit=10_000))
    assert seed(conn, content) == []
    assert world.get_region(conn, "market").light == 5
    assert len(list_events(conn, limit=10_000)) == events_before
