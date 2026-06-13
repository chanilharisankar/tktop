from dataclasses import dataclass

from tktop.metrics.types import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float
    cache_write_per_million: float = 0.0
    cache_read_per_million: float = 0.0


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-6": ModelPricing(15.00, 75.00, 18.75, 1.50),
    "claude-opus-4-8": ModelPricing(15.00, 75.00, 18.75, 1.50),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00, 3.75, 0.30),
    "claude-haiku-4-5": ModelPricing(0.80, 4.00, 1.00, 0.08),
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4.1": ModelPricing(2.00, 8.00, 0.50, 0.50),
}


def calculate_cost(model: str, usage: TokenUsage) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0

    cost = usage.input_tokens * pricing.input_per_million / 1_000_000
    cost += usage.output_tokens * pricing.output_per_million / 1_000_000
    cost += usage.cache_creation_tokens * pricing.cache_write_per_million / 1_000_000
    cost += usage.cache_read_tokens * pricing.cache_read_per_million / 1_000_000
    return cost


def calculate_cost_breakdown(
    model: str, usage: TokenUsage
) -> tuple[float, float, float, float]:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return (0.0, 0.0, 0.0, 0.0)

    return (
        usage.input_tokens * pricing.input_per_million / 1_000_000,
        usage.output_tokens * pricing.output_per_million / 1_000_000,
        usage.cache_creation_tokens * pricing.cache_write_per_million / 1_000_000,
        usage.cache_read_tokens * pricing.cache_read_per_million / 1_000_000,
    )
