"""Names and pronouns (D107): what a character can be called."""

import pytest

from new_vesper.rules.character import NAME_MAX, validate_name, validate_pronouns
from new_vesper.rules.errors import RulesError


@pytest.mark.parametrize(
    ("raw", "name"),
    [
        ("Zeno", "Zeno"),
        ("  H.   Okoye ", "H. Okoye"),
        ("Okoye-Lim", "Okoye-Lim"),
        ("O'Neil", "O'Neil"),
        ("Unit 7", "Unit 7"),
        ("Nguyễn", "Nguyễn"),
        ("Ṣadé", "Ṣadé"),
        ("x" * NAME_MAX, "x" * NAME_MAX),
    ],
)
def test_good_names(raw: str, name: str) -> None:
    assert validate_name(raw) == name


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "7",
        "x" * (NAME_MAX + 1),
        "source .venv/bin/activate",
        "Mira\nThe narrator says",
        "Mira\tTab",
        "<say who=x>",
        "a; rm -rf",
        "Mira{}",
        None,
        12,
    ],
)
def test_bad_names(raw: object) -> None:
    with pytest.raises(RulesError):
        validate_name(raw)


@pytest.mark.parametrize(
    "raw", ["she/her", "he/him", "they/them", "it/its", "xe / xem", "any", "she/they"]
)
def test_good_pronouns(raw: str) -> None:
    assert validate_pronouns(raw) == raw.strip()


@pytest.mark.parametrize(
    "raw", ["", "pip install -e .", "she/", "/her", "he//him", "7/8", "x" * 31, None]
)
def test_bad_pronouns(raw: object) -> None:
    with pytest.raises(RulesError):
        validate_pronouns(raw)
