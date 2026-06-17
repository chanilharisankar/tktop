from tktop.metrics.pricing import MODEL_PRICING, calculate_cost, calculate_cost_breakdown
from tktop.metrics.types import TokenUsage

REQUIRED_PRICED_MODELS_BY_AGENT = {
    "claude-code": [
        "claude-fable-5",
        "claude-mythos-5",
        "claude-opus-4-8",
        "claude-opus-4-7",
        "claude-opus-4-6",
        "claude-opus-4-5",
        "claude-opus-4-1",
        "claude-opus-4",
        "claude-sonnet-4-6",
        "claude-sonnet-4-5",
        "claude-sonnet-4",
        "claude-3-7-sonnet",
        "claude-3-5-sonnet",
        "claude-haiku-4-5",
        "claude-3-5-haiku",
    ],
    "codex": [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.3-codex",
        "gpt-4.1",
        "gpt-4o",
    ],
}

UNPRICED_SUPPORTED_MODELS_BY_AGENT = {
    "codex": {
        "gpt-5.3-codex-spark": (
            "ChatGPT Pro research preview in Codex, with no API token pricing published."
        ),
    },
}


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


def test_calculate_cost_codex_models():
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_read_tokens=100_000,
    )

    assert abs(calculate_cost("gpt-5.5", usage) - 8.05) < 0.001
    assert abs(calculate_cost("gpt-5.4", usage) - 4.025) < 0.001
    assert abs(calculate_cost("gpt-5.4-mini", usage) - 1.2075) < 0.001
    assert abs(calculate_cost("gpt-5.3-codex", usage) - 3.1675) < 0.001


def test_calculate_cost_openai_provider_ids():
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=100_000)

    assert abs(calculate_cost("openai.gpt-5.4", usage) - 4.0) < 0.001
    assert abs(calculate_cost("openai/gpt-5.4", usage) - 4.0) < 0.001


def test_calculate_cost_claude_provider_id_variants():
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_creation_tokens=100_000,
        cache_read_tokens=100_000,
    )

    plain = calculate_cost("claude-haiku-4-5", usage)
    anthropic = calculate_cost("anthropic.claude-haiku-4-5-20251001", usage)
    bedrock = calculate_cost("anthropic.claude-haiku-4-5-20251001-v1:0", usage)
    vertex = calculate_cost("claude-haiku-4-5@20251001", usage)

    assert plain > 0
    assert abs(anthropic - plain) < 0.000001
    assert abs(bedrock - plain) < 0.000001
    assert abs(vertex - plain) < 0.000001


def test_calculate_cost_unknown_model():
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = calculate_cost("unknown-model-xyz", usage)
    assert cost == 0.0


def test_supported_agent_models_have_required_pricing():
    missing = {
        agent: [
            model for model in required_models if model not in MODEL_PRICING
        ]
        for agent, required_models in REQUIRED_PRICED_MODELS_BY_AGENT.items()
    }
    missing = {agent: models for agent, models in missing.items() if models}

    assert missing == {}


def test_required_priced_models_calculate_positive_cost():
    usage = TokenUsage(input_tokens=1000, output_tokens=500, cache_read_tokens=100)
    zero_cost = {
        agent: [
            model for model in required_models if calculate_cost(model, usage) <= 0
        ]
        for agent, required_models in REQUIRED_PRICED_MODELS_BY_AGENT.items()
    }
    zero_cost = {agent: models for agent, models in zero_cost.items() if models}

    assert zero_cost == {}


def test_supported_unpriced_models_are_explicitly_excluded_from_pricing():
    unexpected_priced = {
        agent: [
            model for model in unpriced_models if model in MODEL_PRICING
        ]
        for agent, unpriced_models in UNPRICED_SUPPORTED_MODELS_BY_AGENT.items()
    }
    unexpected_priced = {
        agent: models for agent, models in unexpected_priced.items() if models
    }

    assert unexpected_priced == {}


def test_supported_unpriced_models_have_reason_strings():
    missing_reasons = {
        agent: [
            model
            for model, reason in unpriced_models.items()
            if not reason.strip()
        ]
        for agent, unpriced_models in UNPRICED_SUPPORTED_MODELS_BY_AGENT.items()
    }
    missing_reasons = {
        agent: models for agent, models in missing_reasons.items() if models
    }

    assert missing_reasons == {}


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
