"""Weather that changes gradually (D51): each block depends on the one before."""

from collections.abc import Mapping

from new_vesper.rules.dice import Rng


def next_weather(current: str, transitions: Mapping[str, Mapping[str, int]], rng: Rng) -> str:
    """Pick the next block's weather from the current one's weighted transitions."""
    options = transitions[current]
    total = sum(options.values())
    pick = rng.randint(1, total)
    for state, weight in options.items():
        pick -= weight
        if pick <= 0:
            return state
    raise AssertionError("unreachable: pick exceeded total weight")
