import json
import pathlib

import pytest

from tktop.adapter.codex import CodexAdapter
from tktop.adapter.factory import create_adapter
from tktop.config import Config


@pytest.fixture
def mock_codex_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path
    (root / "session_index.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "codex-session-001",
                        "thread_name": "Fix login bug",
                        "updated_at": "2026-06-13T16:00:00Z",
                    }
                )
            ]
        )
    )

    (root / "config.toml").write_text('model = "gpt-5.5"\n')

    transcript_dir = root / "sessions" / "2026" / "06" / "13"
    transcript_dir.mkdir(parents=True)
    (transcript_dir / "rollout-2026-06-13T16-00-00-codex-session-001.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-06-13T15:58:00.000Z",
                        "type": "session_meta",
                        "payload": {
                            "id": "codex-session-001",
                            "timestamp": "2026-06-13T15:58:00.000Z",
                            "cwd": "/Users/test/project",
                            "originator": "codex-tui",
                            "cli_version": "0.139.0",
                            "source": "cli",
                            "thread_source": "user",
                            "model_provider": "openai",
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:01.000Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "task_started",
                            "turn_id": "t1",
                            "started_at": 1781369601,
                            "model_context_window": 258400,
                            "collaboration_mode_kind": "default",
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:02.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": "fix the login bug"}
                            ],
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:03.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "I’ll inspect the auth code and run the tests.",
                                }
                            ],
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:04.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": "{\"cmd\":\"pytest tests/test_auth.py\"}",
                            "call_id": "call_1",
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:05.000Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {
                                    "input_tokens": 1000,
                                    "cached_input_tokens": 500,
                                    "output_tokens": 200,
                                    "reasoning_output_tokens": 10,
                                    "total_tokens": 1710,
                                },
                                "last_token_usage": {
                                    "input_tokens": 1000,
                                    "cached_input_tokens": 500,
                                    "output_tokens": 200,
                                    "reasoning_output_tokens": 10,
                                    "total_tokens": 1710,
                                },
                                "model_context_window": 258400,
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:06.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "thanks"}],
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:07.000Z",
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {"type": "output_text", "text": "I found the issue and fixed it."}
                            ],
                        },
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-06-13T16:00:08.000Z",
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "info": {
                                "total_token_usage": {
                                    "input_tokens": 1200,
                                    "cached_input_tokens": 700,
                                    "output_tokens": 260,
                                    "reasoning_output_tokens": 12,
                                    "total_tokens": 2172,
                                },
                                "last_token_usage": {
                                    "input_tokens": 200,
                                    "cached_input_tokens": 200,
                                    "output_tokens": 60,
                                    "reasoning_output_tokens": 2,
                                    "total_tokens": 472,
                                },
                                "model_context_window": 258400,
                            },
                        },
                    }
                ),
            ]
        )
    )
    return root


async def test_discover_sessions(mock_codex_dir: pathlib.Path):
    adapter = CodexAdapter(str(mock_codex_dir))
    sessions = await adapter.discover()

    assert len(sessions) == 1
    session = sessions[0]
    assert session.id == "codex-session-001"
    assert session.agent_type == "codex"
    assert session.project_path == "/Users/test/project"
    assert session.title == "Fix login bug"
    assert session.version == "0.139.0"
    assert session.model == "gpt-5.5"


async def test_parse_transcript(mock_codex_dir: pathlib.Path):
    adapter = CodexAdapter(str(mock_codex_dir))
    turns = await adapter.parse_transcript("codex-session-001")

    assistant_turns = [turn for turn in turns if turn.role == "assistant"]
    assert len(assistant_turns) == 2
    assert assistant_turns[0].content_preview.startswith("I’ll inspect")
    assert assistant_turns[0].usage.input_tokens == 1000
    assert assistant_turns[0].usage.output_tokens == 200
    assert assistant_turns[0].usage.cache_read_tokens == 500
    assert assistant_turns[0].tool_calls[0].name == "exec_command"
    assert assistant_turns[0].tool_calls[0].id == "call_1"
    assert assistant_turns[1].usage.output_tokens == 60


async def test_parse_transcript_not_found(mock_codex_dir: pathlib.Path):
    adapter = CodexAdapter(str(mock_codex_dir))
    turns = await adapter.parse_transcript("missing-session")
    assert turns == []


def test_factory_prefers_codex_when_explicit(tmp_path: pathlib.Path):
    claude_dir = tmp_path / "claude"
    codex_dir = tmp_path / "codex"
    claude_dir.mkdir()
    codex_dir.mkdir()
    (codex_dir / "sessions").mkdir()

    cfg = Config(
        session_adapter="codex",
        claude_dir=str(claude_dir),
        codex_dir=str(codex_dir),
    )

    adapter = create_adapter(cfg)
    assert adapter.name == "codex"

