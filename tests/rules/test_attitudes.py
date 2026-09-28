import pytest

from new_vesper.rules.attitudes import Attitude, Axis, parse_axis, shift, validate_attitude
from new_vesper.rules.errors import RulesError


def test_words_cover_the_scale() -> None:
    assert Attitude().words() == {"trust": "neutral", "fondness": "indifferent", "fear": "unafraid"}
    assert Attitude(3, -3, 3).words() == {
        "trust": "trusts completely",
        "fondness": "loathing",
        "fear": "terrified",
    }


def test_one_step_at_a_time() -> None:
    assert shift(Attitude(), Axis.TRUST, 1) == Attitude(1, 0, 0)
    assert shift(Attitude(0, 2, 0), Axis.FONDNESS, -1) == Attitude(0, 1, 0)
    for delta in (2, -2, 0):
        with pytest.raises(RulesError):
            shift(Attitude(), Axis.FEAR, delta)


def test_the_scale_has_ends() -> None:
    with pytest.raises(RulesError, match="end of the scale"):
        shift(Attitude(3, 0, 0), Axis.TRUST, 1)
    with pytest.raises(RulesError):
        shift(Attitude(0, 0, -3), Axis.FEAR, -1)


@pytest.mark.parametrize("values", [(4, 0, 0), (0, -4, 0), (0, 0, 1.5), (True, 0, 0)])
def test_bad_attitudes(values: tuple[object, object, object]) -> None:
    with pytest.raises(RulesError):
        validate_attitude(*values)


def test_axes() -> None:
    assert parse_axis("Trust") is Axis.TRUST
    with pytest.raises(RulesError):
        parse_axis("love")
