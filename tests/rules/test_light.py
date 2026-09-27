import pytest

from new_vesper.rules.errors import RulesError
from new_vesper.rules.light import apply_deed, apply_neglect, encroach, has_fallen


def test_deed_moves_one_and_major_deed_two() -> None:
    assert apply_deed(5, "raise", "deed").after == 6
    assert apply_deed(5, "lower", "deed").after == 4
    assert apply_deed(5, "raise", "major").after == 7
    assert apply_deed(5, "lower", "major").after == 3


def test_light_clamps_at_ten() -> None:
    assert apply_deed(9, "raise", "major").after == 10
    assert apply_deed(10, "raise", "deed").after == 10


def test_reaching_zero_falls_into_old_vesper() -> None:
    change = apply_deed(1, "lower", "major")
    assert change.after == 0
    assert change.fell
    assert has_fallen(0)


def test_already_fallen_does_not_fall_again() -> None:
    assert not encroach(0).fell


def test_encroach_is_minus_one() -> None:
    change = encroach(4)
    assert (change.before, change.after, change.fell) == (4, 3, False)


def test_neglect_per_week() -> None:
    assert apply_neglect(5, 0).after == 5
    assert apply_neglect(5, 3).after == 2
    assert apply_neglect(2, 9).fell


@pytest.mark.parametrize(
    ("current", "direction", "size"),
    [
        (11, "raise", "deed"),
        (-1, "raise", "deed"),
        (5, "up", "deed"),
        (5, "raise", "huge"),
        (5, "raise", 2),
        (5.0, "raise", "deed"),
    ],
)
def test_bad_deed_rejected(current: object, direction: object, size: object) -> None:
    with pytest.raises(RulesError):
        apply_deed(current, direction, size)  # type: ignore[arg-type]


def test_negative_neglect_rejected() -> None:
    with pytest.raises(RulesError):
        apply_neglect(5, -1)
