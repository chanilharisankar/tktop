from datetime import datetime, timezone

from tktop.metrics.aggregator import aggregate
from tktop.metrics.types import SessionInfo, TokenUsage, ToolCall, Turn


def _make_session() -> SessionInfo:
    now = datetime.now(tz=timezone.utc)
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
            timestamp=datetime.now(tz=timezone.utc),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=timezone.utc),
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
            timestamp=datetime.now(tz=timezone.utc),
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
            timestamp=datetime.now(tz=timezone.utc),
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(output_tokens=100),
            tool_calls=[ToolCall(name="Read", id="t1")],
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=timezone.utc),
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
            timestamp=datetime.now(tz=timezone.utc),
            role="assistant",
            model=None,
            usage=TokenUsage(output_tokens=100),
        ),
        Turn(
            number=2,
            timestamp=datetime.now(tz=timezone.utc),
            role="user",
            model=None,
            usage=TokenUsage(),
        ),
        Turn(
            number=3,
            timestamp=datetime.now(tz=timezone.utc),
            role="assistant",
            model=None,
            usage=TokenUsage(output_tokens=250),
        ),
    ]

    result = aggregate(_make_session(), turns)
    assert result.tokens_per_turn == [100, 250]
