"""Season, moon and tide for a place and moment (D56, D57, D59)."""

from dataclasses import dataclass
from datetime import datetime

from new_vesper.content.loader import Content
from new_vesper.content.model import SeasonDef, TideRules
from new_vesper.rules import clock
from new_vesper.rules.resolver import Difficulty
from new_vesper.rules.sky import Moon, Tide, moon, tide
from new_vesper.rules.stats import Stat

RUNG_ORDER = (Difficulty.ROUTINE, Difficulty.RISKY, Difficulty.HARD, Difficulty.DESPERATE)


def season(content: Content, now: datetime) -> SeasonDef | None:
    if content.calendar is None:
        return None
    return content.calendar.season_for_month(clock.city_time(now).month)


@dataclass(frozen=True)
class TideHere:
    tide: Tide
    closed: bool
    note: str | None


def tide_at(rules: TideRules | None, now: datetime) -> TideHere | None:
    """The tide as it matters at a place, or None if the place is out of the tide's reach."""
    if rules is None:
        return None
    current = tide(now)
    conditions = current.conditions
    note = next(
        (rules.notes[c] for c in sorted(conditions, key=len, reverse=True) if c in rules.notes),
        None,
    )
    return TideHere(current, bool(rules.closed_when & conditions), note)


def minimum_rung(
    rules: TideRules | None, stat: Stat, now: datetime
) -> tuple[Difficulty, str] | None:
    """The hardest rung the tide imposes on this stat here right now, with the reason."""
    if rules is None:
        return None
    conditions = tide(now).conditions
    worst: tuple[Difficulty, str] | None = None
    for rule in rules.min_rung:
        if rule.when in conditions and stat.value in rule.stats:
            rung = Difficulty(rule.rung)
            if worst is None or RUNG_ORDER.index(rung) > RUNG_ORDER.index(worst[0]):
                worst = (rung, rule.why)
    return worst


def harder(a: Difficulty, b: Difficulty) -> Difficulty:
    return a if RUNG_ORDER.index(a) >= RUNG_ORDER.index(b) else b


def moon_now(content: Content, now: datetime) -> tuple[Moon, str | None]:
    phase = moon(now)
    note = content.calendar.moon_notes.get(phase.phase) if content.calendar else None
    return phase, note


def describe_sky(content: Content, location_id: str, now: datetime) -> dict[str, object]:
    """What the DM needs about season, moon and tide at a place."""
    place = content.locations[location_id]
    phase, moon_note = moon_now(content, now)
    current = season(content, now)
    sky: dict[str, object] = {
        "season": None
        if current is None
        else {"name": current.name, "description": current.description},
        "moon": {"phase": phase.phase, "meaning": moon_note},
    }
    here = tide_at(place.tide, now)
    if here is not None:
        sky["tide"] = {
            "state": here.tide.state.value,
            "turning": here.tide.turning,
            "spring_tide": here.tide.spring,
            "here": here.note,
            "place_flooded": here.closed,
            "next_high": clock.describe(here.tide.next_high),
            "next_low": clock.describe(here.tide.next_low),
        }
    return sky
