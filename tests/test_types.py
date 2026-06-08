from tktop.metrics.types import TokenUsage


def test_token_usage_total():
    usage = TokenUsage(
        input_tokens=100,
        output_tokens=200,
        cache_creation_tokens=300,
        cache_read_tokens=400,
    )
    assert usage.total == 1000


def test_token_usage_total_zeros():
    usage = TokenUsage(
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
    )
    assert usage.total == 0


def test_token_usage_billable():
    usage = TokenUsage(
        input_tokens=100,
        output_tokens=200,
        cache_creation_tokens=300,
        cache_read_tokens=400,
    )
    assert usage.billable == 300  # only input + output
