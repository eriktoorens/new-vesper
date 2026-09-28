"""Model prices and the cost of one API call, in whole micro-dollars.

Prices are per million tokens and are operator settings: confirm them against
the published pricing page when a model changes. A model with no price here
cannot be called, so nothing runs unmetered.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import Any

# Relative to the model's input price: 5-minute cache writes and cache reads.
CACHE_WRITE_MULTIPLIER = Fraction(5, 4)
CACHE_READ_MULTIPLIER = Fraction(1, 10)


class UnpricedModel(ValueError):
    """A model with no price: refuse to call it rather than spend blind."""


@dataclass(frozen=True)
class ModelPrice:
    input_usd_per_mtok: Fraction
    output_usd_per_mtok: Fraction


PRICES: Mapping[str, ModelPrice] = {
    "claude-sonnet-5": ModelPrice(Fraction(2), Fraction(10)),
    "claude-haiku-4-5": ModelPrice(Fraction(1), Fraction(5)),
}


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0  # uncached input
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @classmethod
    def from_response(cls, usage: Any) -> "TokenUsage":
        """Read an API response's usage object; missing or null fields count as 0."""

        def field(name: str) -> int:
            value = getattr(usage, name, 0) or 0
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"usage.{name} must be a non-negative integer")
            return value

        return cls(
            input_tokens=field("input_tokens"),
            output_tokens=field("output_tokens"),
            cache_read_tokens=field("cache_read_input_tokens"),
            cache_write_tokens=field("cache_creation_input_tokens"),
        )


def price_of(model: str, prices: Mapping[str, ModelPrice] = PRICES) -> ModelPrice:
    try:
        return prices[model]
    except KeyError:
        raise UnpricedModel(f"no price configured for model {model!r}") from None


def cost_micro_usd(model: str, usage: TokenUsage, prices: Mapping[str, ModelPrice] = PRICES) -> int:
    """The call's cost, rounded up to a whole micro-dollar.

    $X per million tokens is exactly X micro-dollars per token.
    """
    price = price_of(model, prices)
    cost = (
        usage.input_tokens * price.input_usd_per_mtok
        + usage.cache_write_tokens * price.input_usd_per_mtok * CACHE_WRITE_MULTIPLIER
        + usage.cache_read_tokens * price.input_usd_per_mtok * CACHE_READ_MULTIPLIER
        + usage.output_tokens * price.output_usd_per_mtok
    )
    return ceil(cost)
