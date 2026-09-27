"""Rolling on loot tables. The DM names a table; code picks the item."""

from new_vesper.content.model import LootEntry, LootTable
from new_vesper.rules.dice import Rng


def roll_loot(table: LootTable, rng: Rng) -> LootEntry:
    """Pick one entry, weighted, using the injected RNG."""
    pick = rng.randint(1, table.total_weight)
    for entry in table.entries:
        pick -= entry.weight
        if pick <= 0:
            return entry
    raise AssertionError("unreachable: pick exceeded total weight")
