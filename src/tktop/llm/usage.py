from __future__ import annotations

from dataclasses import dataclass

from tktop.llm.prompt import SYSTEM_PROMPT
from tktop.metrics.pricing import calculate_cost, get_model_pricing
from tktop.metrics.types import TokenUsage

CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None and self.output_tokens is None:
            return None
        return (
            (self.input_tokens or 0)
            + (self.output_tokens or 0)
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )

    @property
    def has_known_tokens(self) -> bool:
        return self.total_tokens is not None

    def to_token_usage(self) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.input_tokens or 0,
            output_tokens=self.output_tokens or 0,
            cache_creation_tokens=self.cache_creation_tokens,
            cache_read_tokens=self.cache_read_tokens,
        )


@dataclass(frozen=True)
class LLMResult:
    text: str
    usage: LLMUsage | None = None


def estimate_request_usage(prompt: str, *, system_prompt: str = SYSTEM_PROMPT) -> LLMUsage:
    input_tokens = _estimate_tokens("\n\n".join([system_prompt, prompt]))
    return LLMUsage(input_tokens=input_tokens)


def estimate_usage_cost(
    model: str,
    usage: LLMUsage | None,
    *,
    local_model: bool = False,
) -> float | None:
    if local_model or usage is None or not usage.has_known_tokens:
        return None
    if get_model_pricing(model) is None:
        return None
    return calculate_cost(model, usage.to_token_usage())


def _estimate_tokens(text: str) -> int:
    compact = text.strip()
    if not compact:
        return 0
    return max(1, round(len(compact) / CHARS_PER_TOKEN))
