from tktop.metrics.pricing import calculate_cost, MODEL_PRICING
from tktop.metrics.types import TokenUsage


def test_calculate_cost_opus():
    usage = TokenUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_creation_tokens=2000,
        cache_read_tokens=3000,
    )
    cost = calculate_cost("claude-opus-4-6", usage)
    # Input: 1000 * 15.00/1M = 0.015
    # Output: 500 * 75.00/1M = 0.0375
    # CacheWrite: 2000 * 18.75/1M = 0.0375
    # CacheRead: 3000 * 1.50/1M = 0.0045
    expected = 0.0945
    assert abs(cost - expected) < 0.0001


def test_calculate_cost_sonnet():
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)
    cost = calculate_cost("claude-sonnet-4-6", usage)
    # Input: 1M * 3.00/1M = 3.00
    # Output: 100k * 15.00/1M = 1.50
    expected = 4.50
    assert abs(cost - expected) < 0.01


def test_calculate_cost_unknown_model():
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = calculate_cost("unknown-model-xyz", usage)
    assert cost == 0.0


def test_pricing_table_has_expected_models():
    assert "claude-opus-4-6" in MODEL_PRICING
    assert "claude-sonnet-4-6" in MODEL_PRICING
    assert "claude-haiku-4-5" in MODEL_PRICING
    assert "gpt-4o" in MODEL_PRICING
