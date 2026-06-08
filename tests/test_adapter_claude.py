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


@pytest.fixture
def mock_claude_dir_with_transcript(
    mock_claude_dir: pathlib.Path, tools_transcript_path: pathlib.Path
) -> pathlib.Path:
    project_dir = mock_claude_dir / "projects" / "-Users-testuser-Dev-myproject"
    project_dir.mkdir(parents=True)
    shutil.copy(tools_transcript_path, project_dir / "test-session-001.jsonl")
    return mock_claude_dir


async def test_parse_transcript(
    mock_claude_dir_with_transcript: pathlib.Path,
):
    adapter = ClaudeCodeAdapter(str(mock_claude_dir_with_transcript))
    turns = await adapter.parse_transcript("test-session-001")

    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert len(assistant_turns) == 3

    total_tool_calls = sum(len(t.tool_calls) for t in assistant_turns)
    assert total_tool_calls == 5  # Read + Bash + Edit + Bash + Bash

    assert assistant_turns[0].model == "claude-sonnet-4-6"
    assert assistant_turns[0].usage.input_tokens == 150
    assert assistant_turns[0].usage.output_tokens == 200
    assert assistant_turns[0].usage.cache_read_tokens == 8000


async def test_parse_transcript_content_preview(
    mock_claude_dir_with_transcript: pathlib.Path,
):
    adapter = ClaudeCodeAdapter(str(mock_claude_dir_with_transcript))
    turns = await adapter.parse_transcript("test-session-001")

    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert assistant_turns[0].content_preview.startswith("Let me read that.")


async def test_parse_transcript_not_found(mock_claude_dir: pathlib.Path):
    adapter = ClaudeCodeAdapter(str(mock_claude_dir))
    turns = await adapter.parse_transcript("nonexistent-session")
    assert turns == []
