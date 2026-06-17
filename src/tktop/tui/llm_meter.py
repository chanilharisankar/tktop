from __future__ import annotations

from tktop.llm.usage import LLMUsage, estimate_usage_cost


def format_expected_call_meter(
    *,
    provider_label: str,
    model: str,
    usage: LLMUsage,
    local_model: bool,
) -> str:
    input_text = _token_text(usage.input_tokens, approx=True)
    cost_text = _cost_text(
        model,
        usage,
        local_model=local_model,
        prefix="Estimated API-equivalent prompt cost",
    )
    return (
        f"LLM Call API-equivalent Cost: expected {input_text} input tokens with "
        f"{provider_label}. Output tokens and final API-equivalent cost update after "
        f"completion. {cost_text}"
    )


def format_actual_call_meter(
    *,
    provider_label: str,
    model: str,
    usage: LLMUsage | None,
    local_model: bool,
) -> str:
    if usage is None or not usage.has_known_tokens:
        return (
            "LLM Call API-equivalent Cost: actual usage unavailable from "
            f"{provider_label}. Provider did not return token counts."
        )

    parts = [
        f"input {_token_text(usage.input_tokens)}",
        f"output {_token_text(usage.output_tokens)}",
    ]
    if usage.cache_creation_tokens:
        parts.append(f"cache write {usage.cache_creation_tokens:,}")
    if usage.cache_read_tokens:
        parts.append(f"cache read {usage.cache_read_tokens:,}")

    total = usage.total_tokens or 0
    cost_text = _cost_text(
        model,
        usage,
        local_model=local_model,
        prefix="Estimated API-equivalent cost",
    )
    return (
        f"LLM Call API-equivalent Cost: actual {', '.join(parts)} = {total:,} tokens "
        f"with {provider_label}. {cost_text}"
    )


def format_cached_call_meter(
    *,
    provider_label: str,
    model: str,
    usage: LLMUsage | None,
    local_model: bool,
) -> str:
    actual = format_actual_call_meter(
        provider_label=provider_label,
        model=model,
        usage=usage,
        local_model=local_model,
    ).removeprefix("LLM Call API-equivalent Cost: actual ")
    return (
        "LLM Call API-equivalent Cost: cached result - no new tokens spent. "
        f"Original call: {actual}"
    )


def _token_text(value: int | None, *, approx: bool = False) -> str:
    if value is None:
        return "unknown"
    prefix = "~" if approx else ""
    return f"{prefix}{value:,}"


def _cost_text(
    model: str,
    usage: LLMUsage,
    *,
    local_model: bool,
    prefix: str,
) -> str:
    if local_model:
        return f"{prefix}: local model / no provider charge."
    cost = estimate_usage_cost(model, usage, local_model=local_model)
    if cost is None:
        return f"{prefix}: unavailable for this model."
    return f"{prefix}: ${cost:.4f}."
