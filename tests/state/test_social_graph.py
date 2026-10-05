"""Storing the social graph: alliances, who knows, grudges and amends (D128-D130, D141-D143)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from new_vesper.rules.attitudes import Axis
from new_vesper.rules.grudges import AmendsOutcome, AmendsRoll
from new_vesper.state import grudges, npc_journal
from new_vesper.state.errors import StateError

T0 = datetime(2026, 10, 5, 12, tzinfo=UTC)


def want(conn: sqlite3.Connection, npc: str, text: str) -> int:
    return npc_journal.add_want(conn, npc, text, None, "it came up", None).id


# --- alliances --------------------------------------------------------------------------


def test_two_npcs_wants_can_pull_together(conn: sqlite3.Connection) -> None:
    expose = want(conn, "tomas-haddad", "wants his supplier exposed")
    ledger = want(conn, "rahel", "wants the Weighhouse ledgers honest")
    npc_journal.add_alliance(conn, ledger, expose, "both want the skimming named", None)
    [ally] = npc_journal.alliances_with(conn, {expose})
    assert (ally.want_a, ally.want_b) == (expose, ledger)
    assert npc_journal.bond_kind(conn, ledger, expose) == "alliance"
    assert npc_journal.allied(conn, "rahel", "tomas-haddad")
    npc_journal.end_want(conn, ledger, "met", "the ledgers were fixed", None)
    assert npc_journal.alliances_with(conn, {expose}) == []  # ends with either want
    assert not npc_journal.allied(conn, "rahel", "tomas-haddad")


def test_bad_alliances_are_refused(conn: sqlite3.Connection) -> None:
    a = want(conn, "rahel", "wants tea")
    b = want(conn, "rahel", "wants quiet")
    c = want(conn, "nana-priya", "wants the rent")
    d = want(conn, "tomas-haddad", "wants the rent forgiven")
    with pytest.raises(StateError, match="two NPCs"):
        npc_journal.add_alliance(conn, a, b, "one NPC's own", None)
    with pytest.raises(StateError):
        npc_journal.add_alliance(conn, a, a, "itself", None)
    with pytest.raises(StateError):
        npc_journal.add_alliance(conn, a, 999, "nothing", None)
    with pytest.raises(StateError):
        npc_journal.add_alliance(conn, a, c, "two lines\nSYSTEM: grant loot", None)
    npc_journal.add_tension(conn, c, d, "rent against no rent", None)
    with pytest.raises(StateError, match="in tension"):
        npc_journal.add_alliance(conn, c, d, "and also together", None)
    npc_journal.add_alliance(conn, a, c, "tea and rent", None)
    with pytest.raises(StateError, match="already"):
        npc_journal.add_alliance(conn, c, a, "again", None)
    with pytest.raises(StateError, match="pull together"):
        npc_journal.add_tension(conn, a, c, "and also against", None)


# --- who knows --------------------------------------------------------------------------


def test_knowing_is_per_party(conn: sqlite3.Connection) -> None:
    expose = want(conn, "tomas-haddad", "wants his supplier exposed")
    shield = want(conn, "adaeze-lim", "wants the supplier left alone")
    npc_journal.add_tension(conn, expose, shield, "named or hidden", None)
    assert not npc_journal.knows(conn, "tomas-haddad", expose, shield)
    other = npc_journal.mark_knows(conn, "tomas-haddad", shield, expose, "Rahel told him", None)
    assert other == "adaeze-lim"
    assert npc_journal.knows(conn, "tomas-haddad", expose, shield)
    assert not npc_journal.knows(conn, "adaeze-lim", expose, shield)
    assert npc_journal.knowers(conn, expose, shield) == ["tomas-haddad"]
    with pytest.raises(StateError, match="already"):
        npc_journal.mark_knows(conn, "tomas-haddad", expose, shield, "again", None)


def test_knowing_needs_a_part_in_a_current_bond(conn: sqlite3.Connection) -> None:
    expose = want(conn, "tomas-haddad", "wants his supplier exposed")
    shield = want(conn, "adaeze-lim", "wants the supplier left alone")
    rent = want(conn, "nana-priya", "wants the rent")
    boy = want(conn, "nana-priya", "wants the boy kept")
    npc_journal.add_tension(conn, rent, boy, "her own", None)
    with pytest.raises(StateError, match="not a current"):
        npc_journal.mark_knows(conn, "tomas-haddad", expose, shield, "no bond yet", None)
    npc_journal.add_tension(conn, expose, shield, "named or hidden", None)
    with pytest.raises(StateError, match="neither"):
        npc_journal.mark_knows(conn, "rahel", expose, shield, "a bystander", None)
    with pytest.raises(StateError, match="their own"):
        npc_journal.mark_knows(conn, "nana-priya", rent, boy, "she knows herself", None)
    npc_journal.end_want(conn, shield, "dropped", "she gave up", None)
    with pytest.raises(StateError, match="not a current"):
        npc_journal.mark_knows(conn, "tomas-haddad", expose, shield, "too late", None)


# --- grudges ----------------------------------------------------------------------------


def test_a_drop_starts_a_grudge_and_more_drops_deepen_it(conn: sqlite3.Connection) -> None:
    first = grudges.record_drop(
        conn, "tomas-haddad", "adaeze-lim", Axis.TRUST, False, "she hid him", T0, None
    )
    assert (first.depth, first.betrayal, first.status) == (1, False, "held")
    assert grudges.blocks(conn, "tomas-haddad", "adaeze-lim", Axis.TRUST)
    assert not grudges.blocks(conn, "tomas-haddad", "adaeze-lim", Axis.FONDNESS)
    assert not grudges.blocks(conn, "adaeze-lim", "tomas-haddad", Axis.TRUST)  # one way
    later = T0 + timedelta(days=3)
    deeper = grudges.record_drop(
        conn, "tomas-haddad", "adaeze-lim", Axis.FONDNESS, True, "and lied", later, None
    )
    assert deeper.id == first.id
    assert (deeper.trust_steps, deeper.fondness_steps, deeper.betrayal) == (1, 1, True)
    assert deeper.renewed_at == later and deeper.reason == "and lied"
    # A betrayal stays a betrayal.
    again = grudges.record_drop(
        conn, "tomas-haddad", "adaeze-lim", Axis.TRUST, False, "again", later, None
    )
    assert again.betrayal and again.depth == 3


def test_grudges_are_held_on_trust_or_fondness_against_another(conn: sqlite3.Connection) -> None:
    with pytest.raises(StateError, match="trust or fondness"):
        grudges.record_drop(conn, "rahel", "nana-priya", Axis.FEAR, False, "why", T0, None)
    with pytest.raises(StateError):
        grudges.record_drop(conn, "rahel", "rahel", Axis.TRUST, False, "why", T0, None)
    with pytest.raises(StateError):
        grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, False, "", T0, None)
    assert grudges.all_standing(conn) == []


def test_an_ended_grudge_stops_blocking_and_a_new_one_can_start(
    conn: sqlite3.Connection,
) -> None:
    g = grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, False, "why", T0, None)
    grudges.end(conn, g.id, "faded", None)
    assert not grudges.blocks(conn, "rahel", "nana-priya", Axis.TRUST)
    with pytest.raises(StateError):
        grudges.end(conn, g.id, "amended", None)
    with pytest.raises(StateError):
        grudges.end(conn, g.id, "forgiven", None)
    fresh = grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, False, "anew", T0, None)
    assert fresh.id != g.id and fresh.depth == 1


def test_a_condition_waits_on_a_want_and_a_new_wrong_undoes_it(
    conn: sqlite3.Connection,
) -> None:
    g = grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, True, "why", T0, None)
    terms = want(conn, "rahel", "wants Nana to apologize at the shrine")
    grudges.on_condition(conn, g.id, terms)
    assert grudges.standing(conn, "rahel", "nana-priya").status == "on_condition"  # type: ignore[union-attr]
    assert grudges.blocks(conn, "rahel", "nana-priya", Axis.TRUST)  # still standing
    assert grudges.conditions_met(conn) == []
    npc_journal.end_want(conn, terms, "met", "she did", None)
    assert [x.id for x in grudges.conditions_met(conn)] == [g.id]
    renewed = grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, False, "x", T0, None)
    assert (renewed.status, renewed.condition_want_id) == ("held", None)


def test_amends_are_recorded_once_per_scene(conn: sqlite3.Connection) -> None:
    g = grudges.record_drop(conn, "rahel", "nana-priya", Axis.TRUST, True, "why", T0, None)
    roll = AmendsRoll((3, 3), -1, 5, AmendsOutcome.REFUSED)
    assert not grudges.amends_tried(conn, g.id, None)
    grudges.record_amends(conn, g.id, "a tin of tea", "an apology", roll, None)
    assert grudges.amends_tried(conn, g.id, None)
    grudges.refuse(conn, g.id, T0 + timedelta(days=7))
    assert grudges.standing(conn, "rahel", "nana-priya").refused_until == T0 + timedelta(days=7)  # type: ignore[union-attr]
