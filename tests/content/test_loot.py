import random
from collections import Counter

from new_vesper.content.loader import load_content
from new_vesper.content.loot import roll_loot
from new_vesper.content.model import LootEntry, LootTable

TABLE = LootTable(
    "t",
    "T",
    (LootEntry("common", "Common", 3), LootEntry("rare", "Rare", 1)),
)


class Fixed:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (1, TABLE.total_weight)
        return self.value


def test_weight_boundaries() -> None:
    assert [roll_loot(TABLE, Fixed(v)).kind for v in (1, 2, 3, 4)] == [
        "common",
        "common",
        "common",
        "rare",
    ]


def test_seeded_distribution_follows_weights() -> None:
    table = load_content().loot_tables["market-stalls"]
    rng = random.Random(1234)
    n = 38_000
    counts = Counter(roll_loot(table, rng).kind for _ in range(n))
    for entry in table.entries:
        expected = entry.weight / table.total_weight
        assert abs(counts[entry.kind] / n - expected) < 0.01


def test_same_seed_same_loot() -> None:
    table = load_content().loot_tables["market-stalls"]
    first = [roll_loot(table, random.Random(5)) for _ in range(5)]
    assert first == [roll_loot(table, random.Random(5)) for _ in range(5)]
