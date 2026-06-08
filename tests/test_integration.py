from pathlib import Path

import pytest

from tktop.adapter.claude import ClaudeCodeAdapter
from tktop.metrics.aggregator import aggregate
from tktop.metrics.drift import detect_drift


@pytest.mark.skipif(
    not Path.home().joinpath(".claude", "sessions").exists(),
    reason="no ~/.claude/sessions/ directory",
)
async def test_real_claude_data():
    claude_dir = str(Path.home() / ".claude")
    adapter = ClaudeCodeAdapter(claude_dir)

    sessions = await adapter.discover()
    assert len(sessions) > 0, "expected at least 1 session"

    session = sessions[0]
    turns = await adapter.parse_transcript(session.id)

    if not turns:
        pytest.skip("no transcript data for first session")

    metrics = aggregate(session, turns)
    assert metrics.total_usage.total > 0
    assert isinstance(metrics.tool_stats, dict)

    alerts = detect_drift(turns)
    assert isinstance(alerts, list)
