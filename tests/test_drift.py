from datetime import datetime, timezone

from tktop.metrics.drift import detect_drift
from tktop.metrics.types import TokenUsage, ToolCall, Turn

UTC = timezone.utc


def _turn(
    number: int,
    role: str = "assistant",
    output: int = 100,
    tools: list[str] | None = None,
    cache_creation: int = 0,
    cache_read: int = 0,
) -> Turn:
    return Turn(
        number=number,
        timestamp=datetime.now(tz=UTC),
        role=role,
        model="claude-sonnet-4-6",
        usage=TokenUsage(
            output_tokens=output,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        ),
        tool_calls=[ToolCall(name=t, id=f"t{i}") for i, t in enumerate(tools or [])],
    )


# --- Tool Loop ---

def test_tool_loop_detected():
    turns = [
        _turn(1, tools=["Read"]),
        _turn(2, tools=["Read"]),
        _turn(3, tools=["Read"]),
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "tool_loop" for a in alerts)


def test_tool_loop_broken_by_user():
    turns = [
        _turn(1, tools=["Read"]),
        _turn(2, role="user"),
        _turn(3, tools=["Read"]),
        _turn(4, tools=["Read"]),
    ]
    alerts = detect_drift(turns)
    assert not any(a.type == "tool_loop" for a in alerts)


# --- Read Loop ---

def test_read_loop_detected():
    turns = [
        _turn(1, tools=["Read"]),
        _turn(2, role="user"),
        _turn(3, tools=["Read"]),
        _turn(4, role="user"),
        _turn(5, tools=["Read"]),
        _turn(6, role="user"),
        _turn(7, tools=["Read"]),
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "read_loop" for a in alerts)


# --- Edit Thrash ---

def test_edit_thrash_detected():
    turns = [_turn(i + 1, tools=["Edit"]) for i in range(10)]
    alerts = detect_drift(turns)
    assert any(a.type == "edit_thrash" for a in alerts)
    assert any(a.severity == "critical" for a in alerts if a.type == "edit_thrash")


# --- Token Explosion ---

def test_token_explosion_detected():
    turns = [
        _turn(1, output=100),
        _turn(2, output=250),
        _turn(3, output=600),
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "token_explosion" for a in alerts)


def test_token_explosion_not_triggered():
    turns = [
        _turn(1, output=100),
        _turn(2, output=120),
        _turn(3, output=130),
    ]
    alerts = detect_drift(turns)
    assert not any(a.type == "token_explosion" for a in alerts)


# --- Runaway ---

def test_runaway_detected():
    turns = [_turn(i, output=60000) for i in range(12)]
    alerts = detect_drift(turns)
    assert any(a.type == "runaway" for a in alerts)
    assert any(a.severity == "critical" for a in alerts if a.type == "runaway")


def test_runaway_not_triggered_with_user():
    turns = []
    for i in range(12):
        if i == 5:
            turns.append(_turn(i, role="user", output=0))
        else:
            turns.append(_turn(i, output=60000))
    alerts = detect_drift(turns)
    assert not any(a.type == "runaway" for a in alerts)


# --- Permission Loop ---

def test_permission_loop_detected():
    turns = [
        _turn(1, tools=["Bash"]),
        _turn(2, role="user"),
        _turn(3, tools=["Bash"]),
        _turn(4, role="user"),
        _turn(5, tools=["Bash"]),
        _turn(6, role="user"),
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "permission_loop" for a in alerts)


# --- Cache Miss Streak ---

def test_cache_miss_streak_detected():
    turns = [
        _turn(i, cache_creation=5000, cache_read=0) for i in range(1, 7)
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "cache_miss_streak" for a in alerts)


# --- Cost Spike ---

def test_cost_spike_detected():
    turns = [
        _turn(1, output=100),
        _turn(2, output=100),
        _turn(3, output=100),
        _turn(4, output=5000),
    ]
    alerts = detect_drift(turns)
    assert any(a.type == "cost_spike" for a in alerts)


# --- No drift ---

def test_no_drift_normal_session():
    turns = [
        _turn(1, role="user"),
        _turn(2, tools=["Read"], output=100),
        _turn(3, role="user"),
        _turn(4, tools=["Bash"], output=120),
    ]
    alerts = detect_drift(turns)
    assert len(alerts) == 0
