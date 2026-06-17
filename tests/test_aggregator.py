from datetime import datetime, timezone

from tktop.metrics.aggregator import aggregate
from tktop.metrics.types import SessionInfo, TokenUsage, ToolCall, Turn

UTC = timezone.utc


def _make_session() -> SessionInfo:
    now = datetime.now(tz=UTC)
    return SessionInfo(
        id="test-001",
        pid=1234,
        agent_type="claude-code",
        project_path="/dev/test",
        model="claude-sonnet-4-6",
        status="idle",
        started_at=now,
        updated_at=now,
    )


def test_aggregate_totals():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=5000,
                cache_read_tokens=0,
            ),
            tool_calls=[ToolCall(name="Read", id="t1")],
        ),
        Turn(
            number=3,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(
                input_tokens=200,
                output_tokens=120,
                cache_creation_tokens=0,
                cache_read_tokens=5000,
            ),
            tool_calls=[ToolCall(name="Bash", id="t2"), ToolCall(name="Read", id="t3")],
        ),
    ]

    result = aggregate(_make_session(), turns)

    assert result.total_usage.input_tokens == 300
    assert result.total_usage.output_tokens == 170
    assert result.total_usage.cache_creation_tokens == 5000
    assert result.total_usage.cache_read_tokens == 5000
    assert result.total_cost > 0


def test_aggregate_tool_stats():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(output_tokens=100),
            tool_calls=[ToolCall(name="Read", id="t1")],
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(output_tokens=200),
            tool_calls=[
                ToolCall(name="Bash", id="t2"),
                ToolCall(name="Read", id="t3"),
            ],
        ),
    ]

    result = aggregate(_make_session(), turns)

    assert result.tool_stats["Read"].calls == 2
    assert result.tool_stats["Read"].turns_present == 2
    assert result.tool_stats["Bash"].calls == 1
    assert result.tool_stats["Bash"].turns_present == 1


def test_aggregate_tokens_per_turn():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model=None,
            usage=TokenUsage(output_tokens=100),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=3,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model=None,
            usage=TokenUsage(output_tokens=250),
        ),
    ]

    result = aggregate(_make_session(), turns)
    assert result.tokens_per_turn == [100, 250]


def test_aggregate_cost_per_turn_is_cumulative():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=1000, output_tokens=500),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=2000, output_tokens=1000),
        ),
    ]

    result = aggregate(_make_session(), turns)

    assert len(result.cost_per_turn) == 2
    assert result.cost_per_turn[0] > 0
    assert result.cost_per_turn[1] > result.cost_per_turn[0]
    assert abs(result.cost_per_turn[-1] - result.total_cost) < 0.0001


def test_aggregate_cost_per_turn_skips_user_turns():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=1000, output_tokens=500),
        ),
        Turn(
            number=3,
            timestamp=datetime.now(tz=UTC),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
    ]

    result = aggregate(_make_session(), turns)
    assert len(result.cost_per_turn) == 1


def test_aggregate_cost_per_turn_empty():
    result = aggregate(_make_session(), [])
    assert result.cost_per_turn == []


def test_aggregate_turn_costs_breakdown():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(
                input_tokens=1_000_000,
                output_tokens=100_000,
                cache_creation_tokens=50_000,
                cache_read_tokens=200_000,
            ),
        ),
    ]

    result = aggregate(_make_session(), turns)

    assert len(result.turn_costs) == 1
    tc = result.turn_costs[0]
    assert tc.turn_number == 1
    assert abs(tc.input_cost - 3.0) < 0.01
    assert abs(tc.output_cost - 1.5) < 0.01
    assert abs(tc.cache_write_cost - 0.1875) < 0.001
    assert abs(tc.cache_read_cost - 0.06) < 0.001
    assert abs(tc.total - (3.0 + 1.5 + 0.1875 + 0.06)) < 0.01


def test_aggregate_prices_dated_claude_model_id():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-20250514",
            usage=TokenUsage(input_tokens=1_000_000, output_tokens=100_000),
        ),
    ]

    result = aggregate(_make_session(), turns)

    assert abs(result.total_cost - 4.5) < 0.01
    assert len(result.turn_costs) == 1
    assert abs(result.turn_costs[0].total - 4.5) < 0.01


def test_aggregate_turn_costs_skips_user_turns():
    turns = [
        Turn(
            number=1,
            timestamp=datetime.now(tz=UTC),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=UTC),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=1000, output_tokens=500),
        ),
    ]

    result = aggregate(_make_session(), turns)
    assert len(result.turn_costs) == 1
    assert result.turn_costs[0].turn_number == 2


def test_aggregate_turn_costs_empty():
    result = aggregate(_make_session(), [])
    assert result.turn_costs == []
