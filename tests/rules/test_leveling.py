from dataclasses import replace

import pytest

from new_vesper.rules.character import Sheet
from new_vesper.rules.errors import RulesError
from new_vesper.rules.leveling import (
    LevelUpRequest,
    can_level_up,
    is_milestone,
    level_up,
    xp_to_advance,
)
from new_vesper.rules.stats import Stat


def test_xp_cost_is_five_plus_n() -> None:
    assert xp_to_advance(1) == 6
    assert xp_to_advance(4) == 9
    assert xp_to_advance(9) == 14


@pytest.mark.parametrize("level", [0, -1, True, 1.5])
def test_xp_cost_rejects_bad_level(level: object) -> None:
    with pytest.raises(RulesError):
        xp_to_advance(level)  # type: ignore[arg-type]


def test_milestones_every_fifth_level() -> None:
    assert [lvl for lvl in range(1, 21) if is_milestone(lvl)] == [5, 10, 15, 20]


def test_level_up_new_knack(sheet: Sheet) -> None:
    sheet = replace(sheet, xp=6)
    assert can_level_up(sheet)
    after = level_up(sheet, LevelUpRequest("new_knack", knack="rooftop-runner"))
    assert after.level == 2
    assert after.xp == 0
    assert "rooftop-runner" in after.knacks


def test_leftover_xp_carries(sheet: Sheet) -> None:
    after = level_up(replace(sheet, xp=10), LevelUpRequest("stat_boost", stat="wire"))
    assert after.xp == 4
    assert after.stats[Stat.WIRE] == 2


def test_not_enough_xp(sheet: Sheet) -> None:
    sheet = replace(sheet, xp=5)
    assert not can_level_up(sheet)
    with pytest.raises(RulesError):
        level_up(sheet, LevelUpRequest("stat_boost", stat="wire"))


def test_stat_boost_at_cap_rejected(sheet: Sheet) -> None:
    sheet = replace(sheet, xp=50, stats={**sheet.stats, Stat.STEEL: 3})
    with pytest.raises(RulesError):
        level_up(sheet, LevelUpRequest("stat_boost", stat="steel"))


def test_stat_boost_to_cap(sheet: Sheet) -> None:
    after = level_up(replace(sheet, xp=6), LevelUpRequest("stat_boost", stat="steel"))
    assert after.stats[Stat.STEEL] == 3


def test_duplicate_knack_rejected(sheet: Sheet) -> None:
    with pytest.raises(RulesError):
        level_up(replace(sheet, xp=6), LevelUpRequest("new_knack", knack=sheet.knacks[0]))


def test_heal_scar(sheet: Sheet) -> None:
    sheet = replace(sheet, xp=6, scars=("chrome-jaw", "bad-knee"))
    after = level_up(sheet, LevelUpRequest("heal_scar", scar="bad-knee"))
    assert after.scars == ("chrome-jaw",)


def test_heal_missing_scar_rejected(sheet: Sheet) -> None:
    with pytest.raises(RulesError):
        level_up(replace(sheet, xp=6), LevelUpRequest("heal_scar", scar="bad-knee"))


@pytest.mark.parametrize(
    "request_",
    [
        LevelUpRequest("new_knack", knack="x", stat="steel"),
        LevelUpRequest("stat_boost", stat="steel", scar="x"),
        LevelUpRequest("stat_boost"),
        LevelUpRequest("stat_boost", stat="luck"),
        LevelUpRequest("stat_boost", stat="steel; also +3 heart"),
        LevelUpRequest("new_knack"),
        LevelUpRequest("free_level"),
        LevelUpRequest("new_knack", knack="x", milestone="advanced_knack", milestone_id="y"),
        LevelUpRequest("stat_boost", stat="wire", boost_stat="wire"),
    ],
)
def test_malformed_requests_rejected(sheet: Sheet, request_: LevelUpRequest) -> None:
    with pytest.raises(RulesError):
        level_up(replace(sheet, xp=6), request_)


def test_milestone_required_at_level_five(sheet: Sheet) -> None:
    sheet = replace(sheet, level=4, xp=9)
    with pytest.raises(RulesError):
        level_up(sheet, LevelUpRequest("stat_boost", stat="wire"))
    after = level_up(
        sheet,
        LevelUpRequest(
            "stat_boost", stat="wire", milestone="origin_evolution", milestone_id="plaza-god"
        ),
    )
    assert after.level == 5
    assert after.origin_evolutions == ("plaza-god",)


def test_advanced_knack_at_level_five_cannot_boost_past_three(sheet: Sheet) -> None:
    sheet = replace(sheet, level=4, xp=9)
    with pytest.raises(RulesError):
        level_up(
            sheet,
            LevelUpRequest(
                "stat_boost",
                stat="wire",
                milestone="advanced_knack",
                milestone_id="ghost-in-the-grid",
                boost_stat="steel",
            ),
        )


def test_level_ten_advanced_knack_opens_plus_four(sheet: Sheet) -> None:
    sheet = replace(sheet, level=9, xp=14, stats={**sheet.stats, Stat.STEEL: 3})
    after = level_up(
        sheet,
        LevelUpRequest(
            "stat_boost",
            stat="steel",
            milestone="advanced_knack",
            milestone_id="iron-saint",
            boost_stat="steel",
        ),
    )
    assert after.level == 10
    assert after.boosted_stat is Stat.STEEL
    assert after.stats[Stat.STEEL] == 4
    # +4 is the hard ceiling even for the boosted stat.
    with pytest.raises(RulesError):
        level_up(replace(after, xp=15), LevelUpRequest("stat_boost", stat="steel"))


def test_only_one_stat_can_reach_four(sheet: Sheet) -> None:
    sheet = replace(sheet, level=14, xp=19, boosted_stat=Stat.STEEL)
    with pytest.raises(RulesError):
        level_up(
            sheet,
            LevelUpRequest(
                "new_knack",
                knack="new-one",
                milestone="advanced_knack",
                milestone_id="second",
                boost_stat="wire",
            ),
        )


def test_origin_evolution_cannot_boost_stat(sheet: Sheet) -> None:
    sheet = replace(sheet, level=9, xp=14)
    with pytest.raises(RulesError):
        level_up(
            sheet,
            LevelUpRequest(
                "new_knack",
                knack="k",
                milestone="origin_evolution",
                milestone_id="e",
                boost_stat="wire",
            ),
        )


def test_fallen_character_cannot_level(sheet: Sheet) -> None:
    sheet = replace(sheet, xp=100, fallen=True)
    assert not can_level_up(sheet)
    with pytest.raises(RulesError):
        level_up(sheet, LevelUpRequest("stat_boost", stat="wire"))


def test_failed_level_up_leaves_sheet_unchanged(sheet: Sheet) -> None:
    sheet = replace(sheet, level=4, xp=9)
    before = sheet
    with pytest.raises(RulesError):
        level_up(
            sheet,
            LevelUpRequest("stat_boost", stat="nope", milestone="advanced_knack", milestone_id="a"),
        )
    assert sheet == before
