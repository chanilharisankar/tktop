from datetime import datetime, timezone

from tktop.llm.prompt import build_analysis_prompt
from tktop.metrics.types import (
    Alert,
    SessionInfo,
    SessionMetrics,
    TokenUsage,
    ToolCall,
    ToolStat,
    Turn,
)

UTC = timezone.utc


def _make_metrics() -> SessionMetrics:
    now = datetime.now(tz=UTC)
    session = SessionInfo(
        id="test-001",
        pid=1234,
        agent_type="claude-code",
        project_path="/dev/test",
        model="claude-sonnet-4-6",
        status="idle",
        started_at=now,
        updated_at=now,
    )
    turns = [
        Turn(
            number=1,
            timestamp=now,
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=100, output_tokens=200),
            tool_calls=[ToolCall(name="Bash", id="t1")],
            content_preview="Let me check the code",
        ),
        Turn(
            number=2,
            timestamp=now,
            role="assistant",
            model="claude-sonnet-4-6",
            usage=TokenUsage(input_tokens=150, output_tokens=300),
            tool_calls=[
                ToolCall(name="Read", id="t2"),
                ToolCall(name="Edit", id="t3"),
            ],
            content_preview="Found the issue, fixing now",
        ),
    ]
    return SessionMetrics(
        session=session,
        turns=turns,
        total_usage=TokenUsage(input_tokens=250, output_tokens=500),
        total_cost=0.045,
        tool_stats={
            "Bash": ToolStat(name="Bash", calls=1, turns_present=1),
            "Read": ToolStat(name="Read", calls=1, turns_present=1),
            "Edit": ToolStat(name="Edit", calls=1, turns_present=1),
        },
        alerts=[
            Alert(
                severity="warning",
                type="tool_loop",
                description="Read called 3x in 5 turns",
                detected_at=now,
            ),
        ],
    )


def test_prompt_contains_session_summary():
    prompt = build_analysis_prompt(_make_metrics())
    assert "claude-code" in prompt
    assert "claude-sonnet-4-6" in prompt
    assert "250" in prompt
    assert "500" in prompt
    assert "$0.045" in prompt


def test_prompt_contains_tool_usage():
    prompt = build_analysis_prompt(_make_metrics())
    assert "Bash" in prompt
    assert "Read" in prompt
    assert "Edit" in prompt


def test_prompt_contains_alerts():
    prompt = build_analysis_prompt(_make_metrics())
    assert "tool_loop" in prompt
    assert "Read called 3x" in prompt


def test_prompt_contains_conversation_samples():
    prompt = build_analysis_prompt(_make_metrics())
    assert "Let me check the code" in prompt
    assert "Found the issue" in prompt


def test_prompt_contains_instructions():
    prompt = build_analysis_prompt(_make_metrics())
    assert "3-5" in prompt
    assert "actionable" in prompt
    assert "workflow" in prompt


def test_prompt_no_alerts():
    m = _make_metrics()
    m.alerts = []
    prompt = build_analysis_prompt(m)
    assert "Detected Issues" not in prompt
