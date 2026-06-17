from tktop.llm.usage import LLMUsage, estimate_request_usage, estimate_usage_cost
from tktop.tui.llm_meter import (
    format_actual_call_meter,
    format_cached_call_meter,
    format_expected_call_meter,
)


def test_estimate_request_usage_counts_system_and_prompt():
    usage = estimate_request_usage("Summarize the session.", system_prompt="system")

    assert usage.input_tokens is not None
    assert usage.input_tokens > 0
    assert usage.output_tokens is None


def test_estimate_usage_cost_known_model():
    usage = LLMUsage(input_tokens=1_000_000, output_tokens=100_000)

    cost = estimate_usage_cost("gpt-4o", usage)

    assert cost is not None
    assert abs(cost - 3.5) < 0.001


def test_format_expected_call_meter_shows_prompt_estimate():
    usage = LLMUsage(input_tokens=1234)

    text = format_expected_call_meter(
        provider_label="openai/gpt-4o",
        model="gpt-4o",
        usage=usage,
        local_model=False,
    )

    assert "expected ~1,234 input tokens" in text
    assert "Estimated API-equivalent prompt cost" in text


def test_format_actual_call_meter_shows_actual_usage_and_cost():
    usage = LLMUsage(input_tokens=1000, output_tokens=500)

    text = format_actual_call_meter(
        provider_label="openai/gpt-4o",
        model="gpt-4o",
        usage=usage,
        local_model=False,
    )

    assert "actual input 1,000, output 500 = 1,500 tokens" in text
    assert "Estimated API-equivalent cost" in text


def test_format_cached_call_meter_marks_no_new_spend():
    usage = LLMUsage(input_tokens=1000, output_tokens=500)

    text = format_cached_call_meter(
        provider_label="openai/gpt-4o",
        model="gpt-4o",
        usage=usage,
        local_model=False,
    )

    assert "cached result - no new tokens spent" in text
    assert "Original call" in text


def test_format_local_model_meter_shows_no_provider_charge():
    usage = LLMUsage(input_tokens=1000, output_tokens=500)

    text = format_actual_call_meter(
        provider_label="ollama/llama3",
        model="llama3",
        usage=usage,
        local_model=True,
    )

    assert "local model / no provider charge" in text
