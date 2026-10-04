"""Bodily needs (D83-D89): levels, time, penalties and the worst level."""

import pytest

from new_vesper.rules.errors import RulesError
from new_vesper.rules.needs import (
    HOUR,
    NEED_MAX,
    RECOVER_SECONDS,
    STEP_SECONDS,
    WORST_TRACK,
    Climate,
    Exposure,
    Need,
    NeedState,
    advance,
    exposure,
    parse_need,
    penalty,
    roll_stat,
    words,
)
from new_vesper.rules.stats import Stat
from new_vesper.rules.tracks import Track

NONE = Exposure.NONE


def test_hunger_climbs_a_step_per_interval() -> None:
    step = STEP_SECONDS[Need.HUNGER]
    assert advance(Need.HUNGER, NeedState(), step - 1, NONE).after == NeedState(0, step - 1)
    assert advance(Need.HUNGER, NeedState(), step, NONE).after == NeedState(1, 0)
    assert advance(Need.HUNGER, NeedState(1, step - 1), 1, NONE).after == NeedState(2, 0)


def test_thirst_is_fastest_and_tiredness_slowest() -> None:
    assert STEP_SECONDS[Need.THIRST] < STEP_SECONDS[Need.HUNGER] < STEP_SECONDS[Need.TIRED]


def test_reaching_the_worst_level_owes_a_box() -> None:
    step = STEP_SECONDS[Need.THIRST]
    change = advance(Need.THIRST, NeedState(2, 0), step, NONE)
    assert change.after.level == NEED_MAX and change.worst_steps == 1


def test_each_step_at_the_worst_owes_another() -> None:
    step = STEP_SECONDS[Need.THIRST]
    change = advance(Need.THIRST, NeedState(), 5 * step + 7, NONE)
    # 1, 2, 3 (owes), 3 (owes), 3 (owes)
    assert change.after == NeedState(NEED_MAX, 7)
    assert change.worst_steps == 3


def test_below_the_worst_nothing_is_owed() -> None:
    step = STEP_SECONDS[Need.HUNGER]
    assert advance(Need.HUNGER, NeedState(), 2 * step, NONE).worst_steps == 0


def test_tiredness_costs_fade_and_the_rest_harm() -> None:
    assert WORST_TRACK[Need.TIRED] is Track.FADE
    assert {WORST_TRACK[n] for n in Need if n is not Need.TIRED} == {Track.HARM}


@pytest.mark.parametrize("weather", list(Exposure))
def test_clock_needs_ignore_the_weather(weather: Exposure) -> None:
    step = STEP_SECONDS[Need.HUNGER]
    assert advance(Need.HUNGER, NeedState(), step, weather).after.level == 1


def test_cold_rises_only_out_in_the_cold() -> None:
    assert advance(Need.COLD, NeedState(), HOUR, Exposure.COLD).after.level == 1
    assert advance(Need.COLD, NeedState(), 5 * HOUR, Exposure.HOT).after == NeedState()
    assert advance(Need.HEAT, NeedState(), HOUR, Exposure.HOT).after.level == 1
    assert advance(Need.HEAT, NeedState(), HOUR, Exposure.COLD).after == NeedState()


def test_out_of_the_cold_a_body_recovers() -> None:
    change = advance(Need.COLD, NeedState(3, 0), RECOVER_SECONDS + 5, NONE)
    assert change.after == NeedState(2, 5, easing=True) and change.worst_steps == 0
    assert advance(Need.COLD, NeedState(3, 0), 10 * RECOVER_SECONDS, NONE).after == NeedState()
    assert advance(Need.HEAT, NeedState(2, 0), RECOVER_SECONDS, Exposure.COLD).after.level == 1


def test_time_toward_climbing_never_counts_toward_easing() -> None:
    # Fourth playtest: 25 minutes left over from the climb, then 10 minutes indoors,
    # eased a step that should have taken 30.
    climbed = NeedState(3, 25 * 60)
    assert advance(Need.COLD, climbed, 10 * 60, NONE).after == NeedState(3, 10 * 60, easing=True)
    assert advance(Need.COLD, climbed, RECOVER_SECONDS, NONE).after.level == 2


def test_time_toward_easing_never_counts_toward_climbing() -> None:
    eased = NeedState(2, RECOVER_SECONDS - 60, easing=True)
    assert advance(Need.COLD, eased, 40 * 60, Exposure.COLD).after == NeedState(2, 40 * 60)
    assert advance(Need.COLD, eased, HOUR, Exposure.COLD).after.level == 3


def test_easing_keeps_counting_the_same_way() -> None:
    half = NeedState(2, RECOVER_SECONDS // 2, easing=True)
    assert advance(Need.COLD, half, RECOVER_SECONDS // 2, NONE).after.level == 1


def test_no_time_changes_nothing() -> None:
    for need in Need:
        assert advance(need, NeedState(2, 10), 0, NONE).after.level == 2


def test_bad_inputs() -> None:
    with pytest.raises(ValueError):
        advance(Need.HUNGER, NeedState(), -1, NONE)
    with pytest.raises(RulesError):
        advance(Need.HUNGER, NeedState(), 1.5, NONE)  # type: ignore[arg-type]
    with pytest.raises(RulesError):
        NeedState(4, 0)
    with pytest.raises(ValueError):
        NeedState(0, -1)
    with pytest.raises(ValueError):
        NeedState(1, 0, easing="yes")  # type: ignore[arg-type]
    with pytest.raises(RulesError):
        parse_need("boredom")
    assert parse_need(" Hunger ") is Need.HUNGER


def test_penalties_start_at_level_two_and_stack() -> None:
    assert penalty(Stat.STEEL, {Need.HUNGER: 1}) == 0
    assert penalty(Stat.STEEL, {Need.HUNGER: 2}) == 1
    assert penalty(Stat.STEEL, {Need.HUNGER: 3}) == 2
    assert penalty(Stat.STEEL, {Need.HUNGER: 3, Need.THIRST: 2}) == 3
    assert penalty(Stat.WEIRD, {n: 3 for n in Need}) == 0


def test_every_need_wears_down_two_stats() -> None:
    for need in Need:
        hit = [s for s in Stat if penalty(s, {need: 2})]
        assert len(hit) == 2


def test_a_roll_stat_never_drops_below_minus_three() -> None:
    assert roll_stat(1, Stat.STEEL, {Need.HUNGER: 2}) == 0
    assert roll_stat(-1, Stat.STEEL, {n: 3 for n in Need}) == -3
    assert roll_stat(-3, Stat.SLICK, {Need.COLD: 3}) == -3
    assert roll_stat(3, Stat.WEIRD, {n: 3 for n in Need}) == 3


def test_exposure_from_place_weather_and_season() -> None:
    cold, hot = Exposure.COLD, Exposure.HOT
    assert exposure(Climate.SHELTERED, cold, cold) is NONE
    assert exposure(Climate.COLD, hot, hot) is cold
    assert exposure(Climate.EXPOSED, hot, cold) is hot  # the weather wins
    assert exposure(Climate.EXPOSED, None, cold) is cold
    assert exposure(Climate.EXPOSED, None, None) is NONE


def test_words_for_every_level() -> None:
    for need in Need:
        assert len({words(need, level) for level in range(NEED_MAX + 1)}) == NEED_MAX + 1
    with pytest.raises(RulesError):
        words(Need.HUNGER, 4)
