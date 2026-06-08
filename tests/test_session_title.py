import json
import pathlib

from tktop.adapter.claude import ClaudeCodeAdapter


async def test_read_title_from_transcript(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_data = {
        "pid": 12345,
        "sessionId": "test-title-001",
        "cwd": "/Users/testuser/Dev/myproject",
        "startedAt": 1779088912957,
        "status": "idle",
        "updatedAt": 1779088920000,
    }
    (sessions_dir / "12345.json").write_text(json.dumps(session_data))

    project_dir = tmp_path / "projects" / "-Users-testuser-Dev-myproject"
    project_dir.mkdir(parents=True)
    title_entry = {
        "type": "ai-title",
        "aiTitle": "Fix login bug in auth flow",
        "sessionId": "test-title-001",
    }
    user_entry = {
        "type": "user",
        "message": {"role": "user", "content": "fix it"},
        "timestamp": "2026-06-01T10:00:00.000Z",
        "sessionId": "test-title-001",
    }
    lines = [json.dumps(title_entry), json.dumps(user_entry)]
    (project_dir / "test-title-001.jsonl").write_text("\n".join(lines))

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()

    assert len(sessions) == 1
    assert sessions[0].title == "Fix login bug in auth flow"


async def test_read_title_missing_transcript(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_data = {
        "pid": 99999,
        "sessionId": "no-transcript",
        "cwd": "/Users/testuser/Dev/other",
        "startedAt": 1779088912957,
        "status": "idle",
        "updatedAt": 1779088920000,
    }
    (sessions_dir / "99999.json").write_text(json.dumps(session_data))

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()

    assert len(sessions) == 1
    assert sessions[0].title == ""


async def test_read_title_no_ai_title_entry(tmp_path: pathlib.Path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_data = {
        "pid": 11111,
        "sessionId": "no-title",
        "cwd": "/Users/testuser/Dev/proj",
        "startedAt": 1779088912957,
        "status": "idle",
        "updatedAt": 1779088920000,
    }
    (sessions_dir / "11111.json").write_text(json.dumps(session_data))

    project_dir = tmp_path / "projects" / "-Users-testuser-Dev-proj"
    project_dir.mkdir(parents=True)
    mode_entry = {"type": "mode", "mode": "normal", "sessionId": "no-title"}
    user_entry = {
        "type": "user",
        "message": {"role": "user", "content": "hello"},
        "timestamp": "2026-06-01T10:00:00.000Z",
        "sessionId": "no-title",
    }
    lines = [json.dumps(mode_entry), json.dumps(user_entry)]
    (project_dir / "no-title.jsonl").write_text("\n".join(lines))

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()

    assert len(sessions) == 1
    assert sessions[0].title == ""
