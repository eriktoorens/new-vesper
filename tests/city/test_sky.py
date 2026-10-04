"""Seasons, the moon and the tides, and what they do in play."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from new_vesper.city.npcs import agenda
from new_vesper.city.sky import describe_sky, minimum_rung, season, tide_at
from new_vesper.content.loader import Content, load_content
from new_vesper.rules.resolver import Difficulty
from new_vesper.rules.sky import SYNODIC_DAYS, TideState, moon, tide
from new_vesper.rules.stats import Stat


@pytest.fixture(scope="module")
def content() -> Content:
    return load_content()


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


@pytest.mark.parametrize(
    ("moment", "phase"),
    [
        (utc(2026, 9, 26, 17), "full moon"),  # full moon 26 Sep 2026, 16:49 UTC
        (utc(2026, 10, 10, 16), "new moon"),  # new moon 10 Oct 2026, 15:50 UTC
        (utc(2026, 10, 3, 12), "last quarter"),
        (utc(2026, 10, 18, 16), "first quarter"),
    ],
)
def test_moon_phases_match_the_real_sky(moment: datetime, phase: str) -> None:
    assert moon(moment).phase == phase


def test_moon_cycle_and_illumination() -> None:
    full = moon(utc(2026, 9, 26, 17))
    assert full.illumination > 0.99 and full.spring
    later = moon(utc(2026, 9, 26, 17) + timedelta(days=SYNODIC_DAYS))
    assert later.phase == "full moon"
    assert not moon(utc(2026, 10, 3, 12)).spring


def test_two_tides_a_day_about_50_minutes_later() -> None:
    start = utc(2026, 9, 28, 0)
    highs = []
    moment = start
    while len(highs) < 3:
        moment = tide(moment).next_high
        highs.append(moment)
    gap = highs[2] - highs[0]
    assert timedelta(hours=24, minutes=40) < gap < timedelta(hours=25)
    states = {tide(start + timedelta(hours=h)).state for h in range(13)}
    assert states == set(TideState)


def test_spring_tides_run_bigger() -> None:
    spring = max(abs(tide(utc(2026, 9, 26) + timedelta(minutes=10 * n)).height) for n in range(80))
    neap = max(abs(tide(utc(2026, 10, 3) + timedelta(minutes=10 * n)).height) for n in range(80))
    assert spring > neap + 0.4


def test_city_seasons(content: Content) -> None:
    assert season(content, utc(2026, 9, 28, 12)).name == "the Gales"
    assert season(content, utc(2027, 1, 15, 12)).id == "long-wet"
    assert season(content, utc(2026, 7, 4, 12)).id == "steam"
    assert season(content, utc(2026, 11, 1, 3)).id == "gales"  # still 31 Oct in the city


def _find(condition: Any, start: datetime) -> datetime:
    moment = start
    for _ in range(2000):
        if condition(tide(moment)):
            return moment
        moment += timedelta(minutes=10)
    raise AssertionError("no such tide")


def test_mudflats_flood(content: Content) -> None:
    rules = content.locations["the-mudflats"].tide
    low = _find(lambda t: t.state is TideState.LOW, utc(2026, 10, 3))
    high = _find(lambda t: t.state is TideState.HIGH, utc(2026, 10, 3))
    assert not tide_at(rules, low).closed
    assert tide_at(rules, high).closed
    assert tide_at(content.locations["tarp-row"].tide, high) is None


def test_drowned_station_closes_only_at_spring_high(content: Content) -> None:
    rules = content.locations["drowned-station"].tide
    neap_high = _find(lambda t: t.state is TideState.HIGH and not t.spring, utc(2026, 10, 3))
    spring_high = _find(lambda t: t.state is TideState.HIGH and t.spring, utc(2026, 9, 25))
    assert not tide_at(rules, neap_high).closed
    assert tide_at(rules, spring_high).closed


def test_tide_imposes_rungs(content: Content) -> None:
    stairs = content.locations["tidewater-stairs"].tide
    turning = _find(lambda t: t.turning, utc(2026, 10, 3))
    assert minimum_rung(stairs, Stat.SLICK, turning)[0] is Difficulty.HARD
    assert minimum_rung(stairs, Stat.HEART, turning) is None
    flats = content.locations["the-mudflats"].tide
    high = _find(lambda t: t.state is TideState.HIGH, utc(2026, 10, 3))
    assert minimum_rung(flats, Stat.STEEL, high)[0] is Difficulty.DESPERATE


def test_new_moon_schedule_wins(content: Content) -> None:
    whisker = content.npcs["ferryman-whisker"]
    new_moon_evening = utc(2026, 10, 10, 23)  # 7 pm city time, hours after the new moon
    assert moon(new_moon_evening).phase == "new moon"
    assert agenda(whisker, new_moon_evening).activity.startswith("running the ferry")
    ordinary_evening = utc(2026, 10, 3, 23)
    assert agenda(whisker, ordinary_evening).activity.startswith("poling")


def test_the_dm_sees_the_sky(content: Content) -> None:
    sky = describe_sky(content, "tidewater-stairs", utc(2026, 9, 26, 17))
    assert sky["moon"]["phase"] == "full moon"
    assert sky["moon"]["meaning"].startswith("The forgotten are easier to see")
    assert sky["tide"]["spring_tide"] is True
    assert "tide" not in describe_sky(content, "lantern-arcade", utc(2026, 9, 26, 17))
