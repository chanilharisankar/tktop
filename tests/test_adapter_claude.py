import json
import pathlib
import shutil

import pytest

from tktop.adapter.claude import ClaudeCodeAdapter


@pytest.fixture
def mock_claude_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_data = {
        "pid": 12345,
        "sessionId": "test-session-001",
        "cwd": "/Users/testuser/Dev/myproject",
        "startedAt": 1779088912957,
        "version": "2.1.150",
        "kind": "interactive",
        "entrypoint": "cli",
        "status": "idle",
        "updatedAt": 1779088920000,
    }
    (sessions_dir / "12345.json").write_text(json.dumps(session_data))
    return tmp_path


async def test_discover_sessions(mock_claude_dir: pathlib.Path):
    adapter = ClaudeCodeAdapter(str(mock_claude_dir))
    sessions = await adapter.discover()

    assert len(sessions) == 1
    s = sessions[0]
    assert s.id == "test-session-001"
    assert s.pid == 12345
    assert s.project_path == "/Users/testuser/Dev/myproject"
    assert s.status == "idle"
    assert s.agent_type == "claude-code"


async def test_discover_empty_dir(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()
    assert len(sessions) == 0
