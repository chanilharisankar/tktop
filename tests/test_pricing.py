from tktop.metrics.pricing import MODEL_PRICING, calculate_cost, calculate_cost_breakdown
from tktop.metrics.types import TokenUsage


def test_calculate_cost_opus():
    usage = TokenUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_creation_tokens=2000,
        cache_read_tokens=3000,
    )
    cost = calculate_cost("claude-opus-4-6", usage)
    # Input: 1000 * 5.00/1M = 0.005
    # Output: 500 * 25.00/1M = 0.0125
    # CacheWrite: 2000 * 6.25/1M = 0.0125
    # CacheRead: 3000 * 0.50/1M = 0.0015
    expected = 0.0315
    assert abs(cost - expected) < 0.0001


def test_calculate_cost_sonnet():
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)
    cost = calculate_cost("claude-sonnet-4-6", usage)
    # Input: 1M * 3.00/1M = 3.00
    # Output: 100k * 15.00/1M = 1.50
    expected = 4.50
    assert abs(cost - expected) < 0.01


def test_calculate_cost_current_opus():
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_creation_tokens=100_000,
        cache_read_tokens=100_000,
    )
    cost = calculate_cost("claude-opus-4-8", usage)
    expected = 5.0 + 2.5 + 0.625 + 0.05
    assert abs(cost - expected) < 0.001


def test_calculate_cost_claude_dated_and_provider_ids():
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_creation_tokens=100_000,
        cache_read_tokens=100_000,
    )

    sonnet = calculate_cost("claude-sonnet-4-5-20250929", usage)
    bedrock_haiku = calculate_cost("anthropic.claude-haiku-4-5-20251001-v1:0", usage)
    vertex_haiku = calculate_cost("claude-haiku-4-5@20251001", usage)

    assert abs(sonnet - (3.0 + 1.5 + 0.375 + 0.03)) < 0.001
    assert abs(bedrock_haiku - (1.0 + 0.5 + 0.125 + 0.01)) < 0.001
    assert abs(vertex_haiku - bedrock_haiku) < 0.000001


def test_calculate_cost_unknown_model():
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = calculate_cost("unknown-model-xyz", usage)
    assert cost == 0.0


def test_pricing_table_has_expected_models():
    assert "claude-fable-5" in MODEL_PRICING
    assert "claude-opus-4-8" in MODEL_PRICING
    assert "claude-opus-4-6" in MODEL_PRICING
    assert "claude-sonnet-4-6" in MODEL_PRICING
    assert "claude-sonnet-4-5" in MODEL_PRICING
    assert "claude-haiku-4-5" in MODEL_PRICING
    assert "gpt-4o" in MODEL_PRICING


def test_calculate_cost_breakdown_sonnet():
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_creation_tokens=50_000,
        cache_read_tokens=200_000,
    )
    inp, out, cw, cr = calculate_cost_breakdown("claude-sonnet-4-6", usage)
    assert abs(inp - 3.0) < 0.01
    assert abs(out - 1.5) < 0.01
    assert abs(cw - 0.1875) < 0.001
    assert abs(cr - 0.06) < 0.001


def test_calculate_cost_breakdown_unknown_model():
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    result = calculate_cost_breakdown("unknown-xyz", usage)
    assert result == (0.0, 0.0, 0.0, 0.0)


def test_calculate_cost_breakdown_sums_to_calculate_cost():
    usage = TokenUsage(
        input_tokens=5000,
        output_tokens=2000,
        cache_creation_tokens=1000,
        cache_read_tokens=3000,
    )
    inp, out, cw, cr = calculate_cost_breakdown("claude-opus-4-6", usage)
    total_from_breakdown = inp + out + cw + cr
    total_from_cost = calculate_cost("claude-opus-4-6", usage)
    assert abs(total_from_breakdown - total_from_cost) < 0.000001
