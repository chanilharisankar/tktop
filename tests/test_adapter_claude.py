import json
import pathlib
import shutil

import pytest

from tktop.adapter.claude import ClaudeCodeAdapter
from tktop.metrics.aggregator import aggregate


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


async def test_parse_transcript_dedupes_assistant_message_blocks(
    mock_claude_dir: pathlib.Path,
):
    project_dir = mock_claude_dir / "projects" / "-Users-testuser-Dev-myproject"
    project_dir.mkdir(parents=True)

    usage = {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 100,
        "cache_read_input_tokens": 200,
    }

    def assistant_entry(content: list[dict[str, str]]) -> dict[str, object]:
        return {
            "type": "assistant",
            "timestamp": "2026-06-17T12:00:00Z",
            "message": {
                "id": "msg_001",
                "model": "claude-sonnet-4-6",
                "usage": usage,
                "content": content,
            },
        }

    lines = [
        assistant_entry([{"type": "thinking", "thinking": "Need to inspect files."}]),
        assistant_entry([{"type": "tool_use", "id": "toolu_001", "name": "Read"}]),
        assistant_entry([{"type": "text", "text": "The file needs a small adapter fix."}]),
    ]
    (project_dir / "test-session-001.jsonl").write_text(
        "\n".join(json.dumps(line) for line in lines)
    )

    adapter = ClaudeCodeAdapter(str(mock_claude_dir))
    turns = await adapter.parse_transcript("test-session-001")

    assert len(turns) == 1
    turn = turns[0]
    assert turn.number == 1
    assert turn.usage.input_tokens == 10
    assert turn.usage.output_tokens == 20
    assert turn.usage.cache_creation_tokens == 100
    assert turn.usage.cache_read_tokens == 200
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].name == "Read"
    assert turn.tool_calls[0].id == "toolu_001"
    assert "small adapter fix" in turn.content_preview

    session = (await adapter.discover())[0]
    metrics = aggregate(session, turns)
    assert metrics.total_usage.input_tokens == 10
    assert metrics.total_usage.output_tokens == 20
    assert metrics.total_usage.cache_creation_tokens == 100
    assert metrics.total_usage.cache_read_tokens == 200
    assert len(metrics.turn_costs) == 1
    assert metrics.total_cost > 0


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
