import json
import pathlib
from datetime import UTC, datetime, timedelta

from tktop.adapter.claude import ClaudeCodeAdapter


def _make_session_file(sessions_dir: pathlib.Path, pid: int, session_id: str, cwd: str) -> None:
    data = {
        "pid": pid,
        "sessionId": session_id,
        "cwd": cwd,
        "startedAt": int(datetime.now(tz=UTC).timestamp() * 1000),
        "status": "idle",
        "updatedAt": int(datetime.now(tz=UTC).timestamp() * 1000),
    }
    (sessions_dir / f"{pid}.json").write_text(json.dumps(data))


def _make_transcript(
    project_dir: pathlib.Path,
    session_id: str,
    turns: list[dict],
) -> None:
    lines = [json.dumps(t) for t in turns]
    (project_dir / f"{session_id}.jsonl").write_text("\n".join(lines))


async def test_history_aggregates_by_day(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    _make_session_file(sessions_dir, 1001, "hist-001", "/Users/test/proj")

    project_dir = tmp_path / "projects" / "-Users-test-proj"
    project_dir.mkdir(parents=True)

    now = datetime.now(tz=UTC)
    yesterday = now - timedelta(days=1)

    turns = [
        {
            "type": "assistant",
            "timestamp": now.isoformat(),
            "message": {
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [{"type": "text", "text": "hello"}],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "sessionId": "hist-001",
        },
        {
            "type": "assistant",
            "timestamp": now.isoformat(),
            "message": {
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [{"type": "text", "text": "world"}],
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 100,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "sessionId": "hist-001",
        },
        {
            "type": "assistant",
            "timestamp": yesterday.isoformat(),
            "message": {
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [{"type": "text", "text": "older turn"}],
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 300,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "sessionId": "hist-001",
        },
    ]
    _make_transcript(project_dir, "hist-001", turns)

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()
    assert len(sessions) == 1

    all_turns = await adapter.parse_transcript("hist-001")
    assert len(all_turns) == 3

    today_turns = [t for t in all_turns if t.timestamp.date() == now.date()]
    yesterday_turns = [t for t in all_turns if t.timestamp.date() == yesterday.date()]

    assert len(today_turns) == 2
    assert len(yesterday_turns) == 1

    today_output = sum(t.usage.output_tokens for t in today_turns)
    assert today_output == 150

    yesterday_output = sum(t.usage.output_tokens for t in yesterday_turns)
    assert yesterday_output == 300


async def test_history_skips_old_turns(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    _make_session_file(sessions_dir, 2001, "hist-002", "/Users/test/old")

    project_dir = tmp_path / "projects" / "-Users-test-old"
    project_dir.mkdir(parents=True)

    old = datetime.now(tz=UTC) - timedelta(days=10)

    turns = [
        {
            "type": "assistant",
            "timestamp": old.isoformat(),
            "message": {
                "model": "claude-sonnet-4-6",
                "role": "assistant",
                "content": [{"type": "text", "text": "old turn"}],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                },
            },
            "sessionId": "hist-002",
        },
    ]
    _make_transcript(project_dir, "hist-002", turns)

    adapter = ClaudeCodeAdapter(str(tmp_path))
    all_turns = await adapter.parse_transcript("hist-002")

    assert len(all_turns) == 1
    assert all_turns[0].timestamp.date() == old.date()
