from pathlib import Path

import pytest

from tktop.adapter.codex import CodexAdapter
from tktop.metrics.aggregator import aggregate
from tktop.metrics.drift import detect_drift


@pytest.mark.skipif(
    not Path.home().joinpath(".codex", "sessions").exists(),
    reason="no ~/.codex/sessions/ directory",
)
async def test_real_codex_data():
    codex_dir = str(Path.home() / ".codex")
    adapter = CodexAdapter(codex_dir)

    sessions = await adapter.discover()
    assert len(sessions) > 0, "expected at least 1 Codex session"

    session = sessions[0]
    turns = await adapter.parse_transcript(session.id)

    if not turns:
        pytest.skip("no transcript data for first Codex session")

    metrics = aggregate(session, turns)
    assert metrics.total_usage.total > 0
    assert isinstance(metrics.tool_stats, dict)

    alerts = detect_drift(turns)
    assert isinstance(alerts, list)
