"""Dice. The RNG is always injected so tests can seed it."""

from typing import Protocol


class Rng(Protocol):
    """The subset of ``random.Random`` the rules engine uses."""

    def randint(self, a: int, b: int) -> int: ...


def roll_2d6(rng: Rng) -> tuple[int, int]:
    """Roll two six-sided dice."""
    return rng.randint(1, 6), rng.randint(1, 6)
