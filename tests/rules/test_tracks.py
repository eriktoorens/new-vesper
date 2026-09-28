import pytest

from new_vesper.rules.errors import RulesError
from new_vesper.rules.stats import Stat
from new_vesper.rules.tracks import (
    FadeStatus,
    HarmStatus,
    Track,
    change_track,
    effective_stat,
    fade_status,
    harm_status,
    must_fall_or_endure,
    slips_into_old_vesper,
)


@pytest.mark.parametrize(
    ("boxes", "status"),
    [
        (0, HarmStatus.UNHURT),
        (1, HarmStatus.BRUISED),
        (2, HarmStatus.BRUISED),
        (3, HarmStatus.WOUNDED),
        (4, HarmStatus.WOUNDED),
        (5, HarmStatus.CRITICAL),
        (6, HarmStatus.CRITICAL),
    ],
)
def test_harm_thresholds(boxes: int, status: HarmStatus) -> None:
    assert harm_status(boxes) is status


@pytest.mark.parametrize(
    ("boxes", "status"),
    [
        (0, FadeStatus.SEEN),
        (1, FadeStatus.UNNOTICED),
        (2, FadeStatus.UNNOTICED),
        (3, FadeStatus.UNSEEN),
        (4, FadeStatus.UNSEEN),
        (5, FadeStatus.SLIPPING),
        (6, FadeStatus.SLIPPING),
    ],
)
def test_fade_thresholds(boxes: int, status: FadeStatus) -> None:
    assert fade_status(boxes) is status


@pytest.mark.parametrize("boxes", [-1, 7, True, 2.0])
def test_status_rejects_bad_values(boxes: object) -> None:
    with pytest.raises(RulesError):
        harm_status(boxes)  # type: ignore[arg-type]


def test_track_exactly_filling() -> None:
    change = change_track(Track.HARM, 3, 3)
    assert change.after == 6
    assert change.filled


def test_track_overshoot_clamps_and_fills() -> None:
    change = change_track(Track.FADE, 5, 3)
    assert change.after == 6
    assert change.filled


def test_already_full_track_does_not_refill() -> None:
    change = change_track(Track.HARM, 6, 1)
    assert change.after == 6
    assert not change.filled


def test_one_short_of_full() -> None:
    change = change_track(Track.HARM, 2, 3)
    assert change.after == 5
    assert not change.filled


def test_recovery_clamps_at_zero() -> None:
    change = change_track(Track.FADE, 2, -5)
    assert change.after == 0
    assert not change.filled


@pytest.mark.parametrize(("current", "delta"), [(7, 1), (-1, 1), (2, "1"), (2, 1.5), (2, True)])
def test_change_track_rejects_bad_input(current: object, delta: object) -> None:
    with pytest.raises(RulesError):
        change_track(Track.HARM, current, delta)  # type: ignore[arg-type]


def test_fall_or_endure_only_at_six() -> None:
    assert not must_fall_or_endure(5)
    assert must_fall_or_endure(6)


def test_slip_only_at_six() -> None:
    assert not slips_into_old_vesper(5)
    assert slips_into_old_vesper(6)


@pytest.mark.parametrize("stat", [Stat.STEEL, Stat.SLICK])
def test_harm_penalises_steel_and_slick(stat: Stat) -> None:
    assert effective_stat(stat, 2, 2) == 2
    assert effective_stat(stat, 2, 3) == 1
    assert effective_stat(stat, 2, 4) == 1
    assert effective_stat(stat, 2, 5) == 0
    assert effective_stat(stat, 2, 6) == 0


@pytest.mark.parametrize("stat", [Stat.WIRE, Stat.WEIRD, Stat.HEART])
def test_wounded_leaves_other_stats(stat: Stat) -> None:
    assert effective_stat(stat, 2, 4) == 2


def test_wounded_stat_at_cap() -> None:
    assert effective_stat(Stat.STEEL, 3, 3) == 2


def test_critical_at_the_floor_is_minus_three() -> None:
    assert effective_stat(Stat.SLICK, -1, 5) == -3
