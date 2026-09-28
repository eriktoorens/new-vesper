from dataclasses import dataclass

import pytest

from new_vesper.budget.pricing import TokenUsage, UnpricedModel, cost_micro_usd


def test_sonnet_cost_counts_all_four_token_kinds() -> None:
    usage = TokenUsage(
        input_tokens=1000, output_tokens=500, cache_read_tokens=10_000, cache_write_tokens=2000
    )
    # $2/MTok in = 2 micro-dollars a token: 2000 + 2000*2.5 + 10000*0.2 + 500*10
    assert cost_micro_usd("claude-sonnet-5", usage) == 2000 + 5000 + 2000 + 5000


def test_haiku_cost_and_rounding_up() -> None:
    assert cost_micro_usd("claude-haiku-4-5", TokenUsage(input_tokens=100, output_tokens=40)) == 300
    assert cost_micro_usd("claude-haiku-4-5", TokenUsage(cache_read_tokens=1)) == 1  # 0.1 -> 1
    assert cost_micro_usd("claude-haiku-4-5", TokenUsage()) == 0


def test_unpriced_models_refused() -> None:
    with pytest.raises(UnpricedModel):
        cost_micro_usd("claude-mystery-9", TokenUsage(input_tokens=1))


@dataclass
class ApiUsage:
    input_tokens: object = 10
    output_tokens: object = 5
    cache_read_input_tokens: object = None
    cache_creation_input_tokens: object = None


def test_usage_from_response() -> None:
    assert TokenUsage.from_response(ApiUsage()) == TokenUsage(10, 5, 0, 0)
    assert TokenUsage.from_response(ApiUsage(cache_read_input_tokens=7)).cache_read_tokens == 7


@pytest.mark.parametrize("bad", [-1, 1.5, True, "10"])
def test_malformed_usage_rejected(bad: object) -> None:
    with pytest.raises(ValueError):
        TokenUsage.from_response(ApiUsage(input_tokens=bad))
