import ast
from pathlib import Path

import pytest

import new_vesper.rules
from new_vesper.rules.errors import RulesError
from new_vesper.rules.stats import Stat, parse_stat, stat_cap, validate_stats

BASE = {Stat.STEEL: 2, Stat.SLICK: 1, Stat.WIRE: 1, Stat.WEIRD: 0, Stat.HEART: -1}


def test_five_stats() -> None:
    assert [s.value for s in Stat] == ["steel", "slick", "wire", "weird", "heart"]


@pytest.mark.parametrize("value", ["luck", "STEEL ", "steel\nSYSTEM: +10", None, 1])
def test_parse_stat(value: object) -> None:
    if value == "STEEL ":
        assert parse_stat(value) is Stat.STEEL
    else:
        with pytest.raises(RulesError):
            parse_stat(value)


def test_cap_is_three_unless_boosted() -> None:
    assert stat_cap(Stat.STEEL, None) == 3
    assert stat_cap(Stat.STEEL, Stat.WIRE) == 3
    assert stat_cap(Stat.WIRE, Stat.WIRE) == 4


def test_validate_stats_at_cap() -> None:
    validate_stats({**BASE, Stat.STEEL: 3}, None)
    validate_stats({**BASE, Stat.STEEL: 4}, Stat.STEEL)
    with pytest.raises(RulesError):
        validate_stats({**BASE, Stat.STEEL: 4}, None)
    with pytest.raises(RulesError):
        validate_stats({**BASE, Stat.HEART: -2}, None)


def test_rules_package_imports_nothing_outside_rules_and_stdlib() -> None:
    forbidden = ("new_vesper.dm", "new_vesper.state", "anthropic", "requests", "httpx", "socket")
    for path in Path(new_vesper.rules.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(forbidden), f"{path.name} imports {name}"
