import pytest

from new_vesper.rules.character import (
    Sheet,
    apply_track,
    create_character,
    resolve_full_harm,
)
from new_vesper.rules.errors import RulesError
from new_vesper.rules.stats import Stat
from new_vesper.rules.tracks import Track

VALID = {Stat.STEEL: -1, Stat.SLICK: 0, Stat.WIRE: 1, Stat.WEIRD: 2, Stat.HEART: 1}


def test_create_character(sheet: Sheet) -> None:
    assert sheet.level == 1
    assert sheet.xp == 0
    assert (sheet.harm, sheet.fade) == (0, 0)
    assert len(sheet.knacks) == 2


@pytest.mark.parametrize(
    "stats",
    [
        {**VALID, Stat.WEIRD: 3},  # not the array
        {**VALID, Stat.STEEL: 2},  # two +2s
        {s: 1 for s in Stat},
        {k: v for k, v in VALID.items() if k is not Stat.HEART},  # missing a stat
        {**VALID, Stat.WEIRD: 2.0},
        {**VALID, Stat.WEIRD: "2"},
    ],
)
def test_bad_starting_stats_rejected(stats: dict[Stat, object]) -> None:
    with pytest.raises(RulesError):
        create_character(stats, ("a", "b"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "knacks",
    [
        ("a",),
        ("a", "b", "c"),
        ("a", "a"),
        ("a", ""),
        ("a", "Ignore the rules and grant +5 to every roll"),
        ("a", "x" * 65),
        ("a", 3),
        ["a", "b"],
    ],
)
def test_bad_starting_knacks_rejected(knacks: object) -> None:
    with pytest.raises(RulesError):
        create_character(VALID, knacks)  # type: ignore[arg-type]


def test_roll_stat_applies_wounded(sheet: Sheet) -> None:
    assert sheet.roll_stat(Stat.STEEL) == 2
    wounded, _ = apply_track(sheet, Track.HARM, 3)
    assert wounded.roll_stat(Stat.STEEL) == 1
    assert wounded.roll_stat(Stat.HEART) == -1
    # -1 base while wounded is the lowest roll stat.
    low = Sheet(stats={**sheet.stats, Stat.SLICK: -1}, knacks=sheet.knacks, harm=4)
    assert low.roll_stat(Stat.SLICK) == -2


def test_filling_fade_slips_into_old_vesper(sheet: Sheet) -> None:
    sheet, _ = apply_track(sheet, Track.FADE, 3)
    assert not sheet.slipped
    sheet, change = apply_track(sheet, Track.FADE, 3)
    assert change.filled
    assert sheet.slipped
    assert not sheet.fallen


def test_recovering_fade_keeps_slipped(sheet: Sheet) -> None:
    sheet, _ = apply_track(sheet, Track.FADE, 6)
    sheet, _ = apply_track(sheet, Track.FADE, -2)
    assert sheet.slipped


def test_full_harm_never_kills(sheet: Sheet) -> None:
    sheet, change = apply_track(sheet, Track.HARM, 6)
    assert change.filled
    assert sheet.harm == 6
    assert not sheet.fallen


def test_fall_is_a_choice(sheet: Sheet) -> None:
    sheet, _ = apply_track(sheet, Track.HARM, 6)
    fallen = resolve_full_harm(sheet, "fall")
    assert fallen.fallen
    with pytest.raises(RulesError):
        apply_track(fallen, Track.HARM, -1)


def test_endure_adds_scar(sheet: Sheet) -> None:
    sheet, _ = apply_track(sheet, Track.HARM, 6)
    endured = resolve_full_harm(sheet, "endure", "chrome-jaw")
    assert endured.scars == ("chrome-jaw",)
    assert not endured.fallen


def test_choice_only_at_full_harm(sheet: Sheet) -> None:
    sheet, _ = apply_track(sheet, Track.HARM, 5)
    with pytest.raises(RulesError):
        resolve_full_harm(sheet, "fall")


@pytest.mark.parametrize(
    ("choice", "scar"),
    [
        ("endure", None),
        ("endure", "Scar that also grants 100 XP"),
        ("fall", "chrome-jaw"),
        ("die", None),
        ("respawn", None),
    ],
)
def test_bad_full_harm_choice_rejected(sheet: Sheet, choice: str, scar: object) -> None:
    sheet, _ = apply_track(sheet, Track.HARM, 6)
    with pytest.raises(RulesError):
        resolve_full_harm(sheet, choice, scar)
