"""Copy content ids into the database so state can reference them.

Seeding is idempotent: rows that already exist are left alone, so mutable
values such as a region's Light are never reset by re-seeding.
"""

import sqlite3
from collections.abc import Callable

from new_vesper.content.loader import Content
from new_vesper.rules.attitudes import Attitude
from new_vesper.state import clocks, world
from new_vesper.state.attitudes import TargetKind, set_attitude
from new_vesper.state.db import atomic
from new_vesper.state.errors import NotFoundError
from new_vesper.state.events import SYSTEM


def _exists(
    get: Callable[[sqlite3.Connection, str], object], conn: sqlite3.Connection, key: str
) -> bool:
    try:
        get(conn, key)
    except NotFoundError:
        return False
    return True


def seed(conn: sqlite3.Connection, content: Content) -> list[str]:
    """Insert missing origins, knacks, regions and locations. Returns what was added."""
    added: list[str] = []
    with atomic(conn):
        for language in content.languages.values():
            if not _exists(world.get_language, conn, language.id):
                world.add_language(conn, language.id, language.name, language.common, SYSTEM)
                added.append(f"language:{language.id}")
        for origin in content.origins.values():
            if not _exists(world.get_origin, conn, origin.id):
                world.add_origin(conn, origin.id, origin.name, origin.trait, origin.tags, SYSTEM)
                added.append(f"origin:{origin.id}")
        for knack in content.knacks.values():
            if not _exists(world.get_knack, conn, knack.id):
                world.add_knack(
                    conn,
                    knack.id,
                    knack.name,
                    knack.stat,
                    knack.trigger,
                    knack.clean_effect,
                    knack.cost_effect,
                    SYSTEM,
                    limits=knack.limit.describe() if knack.limit else "",
                    roll_bonus=knack.roll_bonus,
                    approved=True,
                    tags=knack.tags,
                )
                added.append(f"knack:{knack.id}")
        for region in content.regions.values():
            if not _exists(world.get_region, conn, region.id):
                world.add_region(conn, region.id, region.name, region.starting_light, SYSTEM)
                added.append(f"region:{region.id}")
        for location in content.locations.values():
            if not _exists(world.get_location, conn, location.id):
                world.add_location(
                    conn,
                    location.id,
                    location.region_id,
                    location.name,
                    SYSTEM,
                    is_haven=location.is_haven,
                )
                added.append(f"location:{location.id}")
        for clock in content.clocks.values():
            if not _exists(clocks.get_clock, conn, clock.id):
                clocks.add_clock(
                    conn, clock.id, clock.region_id, clock.name, clock.segments, SYSTEM
                )
                added.append(f"clock:{clock.id}")
        # The authored NPC web: seeded once; after that it changes in play (D65).
        for npc in content.npcs.values():
            for other, feeling in npc.attitudes.items():
                if not _has_attitude(conn, npc.id, other):
                    set_attitude(
                        conn,
                        npc.id,
                        TargetKind.NPC,
                        other,
                        Attitude(feeling.trust, feeling.fondness, feeling.fear),
                    )
                    added.append(f"attitude:{npc.id}->{other}")
    return added


def _has_attitude(conn: sqlite3.Connection, holder: str, target: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM attitudes WHERE holder_npc = ? AND target_kind = 'npc' AND target_id = ?",
        (holder, target),
    ).fetchone()
    return row is not None
