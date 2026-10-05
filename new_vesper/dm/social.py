"""The social graph at scene close (D127-D130, D141-D144).

The scene-close call proposes alliances, who learned whose part, feeling changes and
amends; code checks each and keeps only what the rules allow. Anything refused is
dropped, never partly applied. NPCs only, for now (D144).
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from new_vesper.content.loader import Content
from new_vesper.dm.prompt import JournalLines
from new_vesper.rules.attitudes import Attitude, Axis, parse_axis
from new_vesper.rules.dice import Rng
from new_vesper.rules.errors import RulesError
from new_vesper.rules.grudges import (
    REFUSED_FOR,
    AmendsOutcome,
    BondKind,
    check_feeling,
    fades,
    is_betrayal,
    makes_grudge,
    needs_amends,
    parse_direction,
    recovery_axis,
    roll_amends,
)
from new_vesper.state import grudges, npc_journal
from new_vesper.state.attitudes import TargetKind, change_attitude, get_attitude
from new_vesper.state.db import atomic
from new_vesper.state.errors import StateError
from new_vesper.state.events import Cause, append_event

# Events from here show in play, through the journal, never in a recap (D125).
SOCIAL_EVENTS = frozenset(
    {
        "npc_wants_allied",
        "npc_learned_part",
        "npc_grudge_held",
        "npc_grudge_ended",
        "npc_amends",
    }
)


@dataclass(frozen=True)
class SceneClose:
    """What applying the social graph needs from the closing scene."""

    conn: sqlite3.Connection
    content: Content
    rng: Rng
    now: datetime
    there: set[str]  # NPCs who were in the scene
    scene_id: int
    cause: Cause


def default_feeling(content: Content, holder: str, target: str) -> Attitude:
    """The authored feeling one NPC starts with toward another (D65), or neutral."""
    authored = content.npcs[holder].attitudes.get(target)
    if authored is None:
        return Attitude()
    return Attitude(authored.trust, authored.fondness, authored.fear)


def apply(close: SceneClose, lines: JournalLines) -> None:
    """Alliances, then who knows, then feelings, then amends: each may rest on the last."""
    for first, second, note in lines.alliances:
        _ally(close, first, second, note)
    for npc_id, first, second, how in lines.knows:
        _learn(close, npc_id, first, second, how)
    for line in lines.feelings:
        _feel(close, *line)
    for wronged, wrongdoer, offer, condition in lines.amends:
        _amends(close, wronged, wrongdoer, offer, condition)


def _ally(close: SceneClose, first: int, second: int, note: str) -> None:
    conn = close.conn
    try:
        owners = {npc_journal.get_active(conn, w).npc_id for w in (first, second)}
        if not owners & close.there:
            return
        ally = npc_journal.add_alliance(conn, first, second, note, close.scene_id)
    except StateError:
        return
    append_event(
        conn,
        "npc_wants_allied",
        close.cause,
        {"wants": [ally.want_a, ally.want_b], "note": ally.note},
    )


def _learn(close: SceneClose, npc_id: str, first: int, second: int, how: str) -> None:
    if npc_id not in close.there:
        return
    try:
        other = npc_journal.mark_knows(close.conn, npc_id, first, second, how, close.scene_id)
    except StateError:
        return
    append_event(
        close.conn,
        "npc_learned_part",
        close.cause,
        {"npc_id": npc_id, "of": other, "wants": sorted((first, second)), "how": how},
    )


def _feel(
    close: SceneClose,
    holder: str,
    toward: str,
    axis_name: str,
    direction_name: str,
    first: int,
    second: int,
    why: str,
) -> None:
    """A feeling moves when an NPC knows the other's part (D127, D128), capped as D61."""
    conn, content = close.conn, close.content
    if holder not in close.there or holder not in content.npcs or toward not in content.npcs:
        return
    try:
        kind, other = npc_journal.parties(conn, first, second, holder)
        if other != toward or not npc_journal.knows(conn, holder, first, second):
            return
        axis = parse_axis(axis_name)
        delta = check_feeling(BondKind(kind), axis, parse_direction(direction_name))
        if delta > 0 and grudges.blocks(conn, holder, toward, axis):
            return  # a grudge keeps it from rising (D143)
        default = default_feeling(content, holder, toward)
        before = get_attitude(conn, holder, TargetKind.NPC, toward, default)
        with atomic(conn):
            change_attitude(
                conn, holder, TargetKind.NPC, toward, axis, delta, why, close.cause,
                default=default,
            )  # fmt: skip
            if makes_grudge(BondKind(kind), axis, delta):
                betrayal = is_betrayal(before.trust, npc_journal.allied(conn, holder, toward))
                grudge = grudges.record_drop(
                    conn, holder, toward, axis, betrayal, why, close.now, close.scene_id
                )
                append_event(
                    conn,
                    "npc_grudge_held",
                    close.cause,
                    {
                        "npc_id": holder,
                        "against": toward,
                        "depth": grudge.depth,
                        "betrayal": grudge.betrayal,
                        "why": why,
                    },
                )
    except (StateError, RulesError, ValueError):
        return


def _amends(close: SceneClose, wronged: str, wrongdoer: str, offer: str, condition: str) -> None:
    """Amends offered on the page, settled by 2d6 + the wronged NPC's fondness (D142)."""
    conn, content = close.conn, close.content
    if not {wronged, wrongdoer} <= close.there or wronged == wrongdoer:
        return
    grudge = grudges.standing(conn, wronged, wrongdoer)
    if grudge is None or grudge.status != "held":
        return
    if grudge.refused_until is not None and close.now < grudge.refused_until:
        return
    if grudges.amends_tried(conn, grudge.id, close.scene_id):
        return
    if len(offer) > 160 or len(condition) > 160:
        return
    default = default_feeling(content, wronged, wrongdoer)
    fondness = get_attitude(conn, wronged, TargetKind.NPC, wrongdoer, default).fondness
    roll = roll_amends(fondness, close.rng)
    with atomic(conn):
        grudges.record_amends(conn, grudge.id, offer, condition, roll, close.scene_id)
        payload: dict[str, Any] = {
            "npc_id": wronged,
            "from": wrongdoer,
            "offer": offer,
            "dice": list(roll.dice),
            "fondness": roll.fondness,
            "total": roll.total,
            "outcome": roll.outcome.value,
        }
        if roll.outcome is AmendsOutcome.ACCEPTED:
            _end_grudge(close, grudge, "amended", "accepted amends: " + offer)
        elif roll.outcome is AmendsOutcome.ON_CONDITION:
            name = content.npcs[wrongdoer].name
            try:
                terms = npc_journal.add_want(
                    conn, wronged, condition, name, f"asked of {name} for amends", close.scene_id
                )
            except StateError:
                payload["condition"] = None  # no room for it: the grudge simply stands
            else:
                grudges.on_condition(conn, grudge.id, terms.id)
                payload["condition"] = terms.want
                append_event(
                    conn,
                    "npc_want_added",
                    close.cause,
                    {"npc_id": wronged, "want_id": terms.id, "want": terms.want,
                     "why": terms.reason},
                )  # fmt: skip
        else:
            grudges.refuse(conn, grudge.id, close.now + REFUSED_FOR)
        append_event(conn, "npc_amends", close.cause, payload)


def _end_grudge(close: SceneClose, grudge: grudges.Grudge, ending: str, why: str) -> None:
    """The grudge ends, and one step of the axis it dropped comes back (D142, D129)."""
    conn = close.conn
    axis = recovery_axis(grudge.trust_steps, grudge.fondness_steps)
    grudges.end(conn, grudge.id, ending, close.scene_id)
    restored: Axis | None = axis
    try:
        change_attitude(
            conn, grudge.holder, TargetKind.NPC, grudge.target, axis, 1, why, close.cause,
            default=default_feeling(close.content, grudge.holder, grudge.target),
        )  # fmt: skip
    except StateError:
        restored = None  # already moved this scene, or at the top of the scale
    append_event(
        conn,
        "npc_grudge_ended",
        close.cause,
        {
            "npc_id": grudge.holder,
            "against": grudge.target,
            "ending": ending,
            "restored": None if restored is None else restored.value,
            "why": why,
        },
    )


def settle(close: SceneClose) -> None:
    """Grudges that end without a roll: conditions met, and light grudges a week old.

    A condition dropped rather than met puts the grudge back to held.
    """
    for grudge in grudges.conditions_ended(close.conn, "met"):
        with atomic(close.conn):
            _end_grudge(close, grudge, "amended", "the condition of amends was met")
    for grudge in grudges.conditions_ended(close.conn, "dropped"):
        grudges.hold(close.conn, grudge.id)
    for grudge in grudges.all_standing(close.conn):
        if grudge.status == "held" and fades(
            grudge.depth, grudge.betrayal, grudge.renewed_at, close.now
        ):
            with atomic(close.conn):
                _end_grudge(close, grudge, "faded", "a week passed and the grudge faded")


def bonds_for_request(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Current tensions and alliances, and who knows the other's part, for scene close."""
    everyone = {w.id for w in npc_journal.active_wants(conn)}
    found: list[dict[str, Any]] = []
    for kind, bonds in (
        ("tension", npc_journal.tensions_with(conn, everyone)),
        ("alliance", npc_journal.alliances_with(conn, everyone)),
    ):
        for b in bonds:
            found.append(
                {
                    "kind": kind,
                    "wants": [b.want_a, b.want_b],
                    "how": b.note,
                    "knows_the_other_part": npc_journal.knowers(conn, b.want_a, b.want_b),
                }
            )
    return found


def grudges_for_request(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "npc": g.holder,
            "against": g.target,
            "needs_amends": needs_amends(g.depth, g.betrayal),
            "waiting_on_condition": g.status == "on_condition",
        }
        for g in grudges.all_standing(conn)
    ]
