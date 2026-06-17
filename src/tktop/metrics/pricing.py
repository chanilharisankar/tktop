import re
from dataclasses import dataclass

from tktop.metrics.types import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float
    cache_write_per_million: float = 0.0
    cache_read_per_million: float = 0.0


BEDROCK_VERSION_SUFFIX_RE = re.compile(r"-v\d(?::\d)?$")
CLAUDE_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")

CLAUDE_FABLE = ModelPricing(10.00, 50.00, 12.50, 1.00)
CLAUDE_OPUS_45_PLUS = ModelPricing(5.00, 25.00, 6.25, 0.50)
CLAUDE_OPUS_4_LEGACY = ModelPricing(15.00, 75.00, 18.75, 1.50)
CLAUDE_SONNET = ModelPricing(3.00, 15.00, 3.75, 0.30)
CLAUDE_HAIKU_45 = ModelPricing(1.00, 5.00, 1.25, 0.10)
CLAUDE_HAIKU_35 = ModelPricing(0.80, 4.00, 1.00, 0.08)


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-fable-5": CLAUDE_FABLE,
    "claude-mythos-5": CLAUDE_FABLE,
    "claude-opus-4-8": CLAUDE_OPUS_45_PLUS,
    "claude-opus-4-7": CLAUDE_OPUS_45_PLUS,
    "claude-opus-4-6": CLAUDE_OPUS_45_PLUS,
    "claude-opus-4-5": CLAUDE_OPUS_45_PLUS,
    "claude-opus-4-1": CLAUDE_OPUS_4_LEGACY,
    "claude-opus-4": CLAUDE_OPUS_4_LEGACY,
    "claude-sonnet-4-6": CLAUDE_SONNET,
    "claude-sonnet-4-5": CLAUDE_SONNET,
    "claude-sonnet-4": CLAUDE_SONNET,
    "claude-3-7-sonnet": CLAUDE_SONNET,
    "claude-3-5-sonnet": CLAUDE_SONNET,
    "claude-haiku-4-5": CLAUDE_HAIKU_45,
    "claude-3-5-haiku": CLAUDE_HAIKU_35,
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4.1": ModelPricing(2.00, 8.00, 0.50, 0.50),
}


def get_model_pricing(model: str) -> ModelPricing | None:
    return MODEL_PRICING.get(_normalize_model_id(model))


def calculate_cost(model: str, usage: TokenUsage) -> float:
    pricing = get_model_pricing(model)
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
    pricing = get_model_pricing(model)
    if pricing is None:
        return (0.0, 0.0, 0.0, 0.0)

    return (
        usage.input_tokens * pricing.input_per_million / 1_000_000,
        usage.output_tokens * pricing.output_per_million / 1_000_000,
        usage.cache_creation_tokens * pricing.cache_write_per_million / 1_000_000,
        usage.cache_read_tokens * pricing.cache_read_per_million / 1_000_000,
    )


def _normalize_model_id(model: str) -> str:
    normalized = model.strip().lower()

    if normalized.startswith("anthropic."):
        normalized = normalized.removeprefix("anthropic.")

    if normalized.startswith("claude-") and "@" in normalized:
        base, _, suffix = normalized.partition("@")
        if suffix.isdigit():
            normalized = f"{base}-{suffix}"

    normalized = BEDROCK_VERSION_SUFFIX_RE.sub("", normalized)

    if normalized in MODEL_PRICING:
        return normalized

    if normalized.startswith("claude-"):
        without_date = CLAUDE_DATE_SUFFIX_RE.sub("", normalized)
        if without_date in MODEL_PRICING:
            return without_date

    return normalized
