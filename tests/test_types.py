from tktop.metrics.types import TokenUsage, TurnCost


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


def test_turn_cost_total():
    tc = TurnCost(
        turn_number=1,
        input_cost=0.50,
        output_cost=0.25,
        cache_write_cost=0.10,
        cache_read_cost=0.05,
    )
    assert abs(tc.total - 0.90) < 0.0001


def test_turn_cost_total_zeros():
    tc = TurnCost(turn_number=1)
    assert tc.total == 0.0
