"""Languages (D41, D76-D81): what a character understands of a line."""

import pytest

from new_vesper.rules.consequences import ConsequenceType
from new_vesper.rules.errors import RulesError
from new_vesper.rules.languages import (
    COMMON_TONGUE,
    MAX_GIBBERISH_WORDS,
    REAL_COSTS,
    Heard,
    check_gist_stat,
    gibberish,
    gist_heard,
    heard,
)
from new_vesper.rules.resolver import Tier
from new_vesper.rules.stats import Stat

SOUNDS = ("ack", "nak", "sync", "hold")


def test_a_clean_gist_roll_hears_the_gist_whatever_else() -> None:
    assert gist_heard(Tier.CLEAN, None) is Heard.GIST


@pytest.mark.parametrize("cost", sorted(REAL_COSTS))
def test_a_real_cost_buys_the_gist(cost: ConsequenceType) -> None:
    assert gist_heard(Tier.COST, cost) is Heard.GIST


@pytest.mark.parametrize("cost", [None, ConsequenceType.NARRATIVE_COST])
def test_a_narrative_cost_or_none_yet_buys_only_the_tone(cost: ConsequenceType | None) -> None:
    assert gist_heard(Tier.COST, cost) is Heard.TONE


@pytest.mark.parametrize("move", list(ConsequenceType))
def test_six_or_less_hears_nothing(move: ConsequenceType) -> None:
    assert gist_heard(Tier.CITY_MOVES, move) is Heard.NONE


def test_real_costs_are_the_ordinary_costs_that_write_state() -> None:
    assert ConsequenceType.NARRATIVE_COST not in REAL_COSTS
    assert {ConsequenceType.DEAL_HARM, ConsequenceType.ADD_FADE} <= REAL_COSTS


def test_a_spoken_language_is_always_fluent() -> None:
    spoken = frozenset({COMMON_TONGUE, "tagalog"})
    assert heard("tagalog", spoken, {"tagalog": Heard.NONE}) is Heard.FLUENT
    assert heard(COMMON_TONGUE, spoken) is Heard.FLUENT


def test_an_unspoken_language_is_what_the_scene_earned_or_nothing() -> None:
    spoken = frozenset({COMMON_TONGUE})
    assert heard("wolof", spoken) is Heard.NONE
    assert heard("wolof", spoken, {"wolof": Heard.TONE}) is Heard.TONE
    assert heard("hindi", spoken, {"wolof": Heard.GIST}) is Heard.NONE


def test_gist_rolls_are_heart() -> None:
    check_gist_stat(Stat.HEART)
    for stat in Stat:
        if stat is not Stat.HEART:
            with pytest.raises(RulesError, match="Heart"):
                check_gist_stat(stat)


def test_gibberish_is_stable_and_hides_the_words() -> None:
    line = "The ferry leaves at midnight, child."
    once = gibberish(line, SOUNDS, "protocol")
    assert once == gibberish(line, SOUNDS, "protocol")
    assert len(once.split()) == len(line.split())
    assert "ferry" not in once.lower() and "midnight" not in once.lower()
    assert once.endswith(".")


def test_gibberish_keeps_questions_and_caps_length() -> None:
    assert gibberish("Who goes there?", SOUNDS).endswith("?")
    long = " ".join(["word"] * 50)
    assert len(gibberish(long, SOUNDS).split()) == MAX_GIBBERISH_WORDS


def test_gibberish_differs_by_language() -> None:
    line = "Meet me under the third lantern when the tide turns."
    assert gibberish(line, SOUNDS, "protocol") != gibberish(line, SOUNDS, "underside-cant")


def test_gibberish_needs_sounds() -> None:
    with pytest.raises(RulesError):
        gibberish("hello", ())
