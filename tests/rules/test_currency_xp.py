import pytest

from new_vesper.rules.currency import STARTING_GLITTER, format_glitter
from new_vesper.rules.errors import RulesError
from new_vesper.rules.xp import Trigger, parse_trigger


@pytest.mark.parametrize(
    ("amount", "text"),
    [
        (0, "0 glitter"),
        (7, "7 glitter"),
        (10, "1 glim"),
        (50, "5 glims"),
        (125, "1 glamour, 2 glims, 5 glitter"),
        (300, "3 glamour"),
    ],
)
def test_format_glitter(amount: int, text: str) -> None:
    assert format_glitter(amount) == text


def test_starting_purse_is_five_glims() -> None:
    assert format_glitter(STARTING_GLITTER) == "5 glims"


@pytest.mark.parametrize("amount", [-1, 1.5, "10"])
def test_bad_amounts(amount: object) -> None:
    with pytest.raises(RulesError):
        format_glitter(amount)  # type: ignore[arg-type]


def test_exactly_four_triggers() -> None:
    assert len(Trigger) == 4
    assert parse_trigger("raise_light") is Trigger.RAISE_LIGHT
    for bad in ("kill_a_monster", "raise_light please", 1):
        with pytest.raises(RulesError):
            parse_trigger(bad)
