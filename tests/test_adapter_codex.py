import json
import pathlib

import pytest

from tktop.adapter.codex import CodexAdapter
from tktop.adapter.factory import create_adapter
from tktop.config import Config
from tktop.metrics.aggregator import aggregate


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


async def test_codex_supported_model_aggregates_nonzero_cost(
    mock_codex_dir: pathlib.Path,
):
    adapter = CodexAdapter(str(mock_codex_dir))
    session = (await adapter.discover())[0]
    turns = await adapter.parse_transcript("codex-session-001")

    metrics = aggregate(session, turns)

    assert metrics.total_usage.input_tokens == 1200
    assert metrics.total_usage.output_tokens == 260
    assert metrics.total_usage.cache_read_tokens == 700
    assert metrics.total_cost > 0
    assert metrics.cost_per_turn[-1] == metrics.total_cost
    assert all(turn_cost.total > 0 for turn_cost in metrics.turn_costs)


async def test_codex_unknown_model_keeps_tokens_but_zero_cost(
    mock_codex_dir: pathlib.Path,
):
    (mock_codex_dir / "config.toml").write_text('model = "gpt-unknown"\n')

    adapter = CodexAdapter(str(mock_codex_dir))
    session = (await adapter.discover())[0]
    turns = await adapter.parse_transcript("codex-session-001")

    metrics = aggregate(session, turns)

    assert metrics.total_usage.total > 0
    assert metrics.total_cost == 0.0
    assert metrics.cost_per_turn == [0.0, 0.0]
    assert all(turn_cost.total == 0.0 for turn_cost in metrics.turn_costs)


async def test_parse_transcript_token_count_edge_cases(tmp_path: pathlib.Path):
    (tmp_path / "session_index.jsonl").write_text(
        json.dumps(
            {
                "id": "codex-edge-session",
                "thread_name": "Token edge cases",
                "updated_at": "2026-06-13T16:00:00Z",
            }
        )
    )
    (tmp_path / "config.toml").write_text('model = "gpt-5.5"\n')

    transcript_dir = tmp_path / "sessions" / "2026" / "06" / "13"
    transcript_dir.mkdir(parents=True)
    transcript = transcript_dir / "rollout-2026-06-13T16-00-00-codex-edge-session.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps(line)
            for line in [
                {
                    "timestamp": "2026-06-13T15:58:00.000Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "codex-edge-session",
                        "timestamp": "2026-06-13T15:58:00.000Z",
                        "cwd": "/Users/test/project",
                        "cli_version": "0.139.0",
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:00.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 999,
                                "cached_input_tokens": 999,
                                "output_tokens": 999,
                            }
                        },
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:01.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "fix bug"}],
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:02.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "I will inspect it."}],
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:03.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {"last_token_usage": "malformed"},
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:04.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 100,
                                "output_tokens": 20,
                            }
                        },
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:05.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "continue"}],
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:06.000Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "I found it."}],
                    },
                },
                {
                    "timestamp": "2026-06-13T16:00:07.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 50,
                                "cached_input_tokens": 5,
                                "output_tokens": 10,
                            }
                        },
                    },
                },
            ]
        )
    )

    adapter = CodexAdapter(str(tmp_path))
    turns = await adapter.parse_transcript("codex-edge-session")

    assistant_turns = [turn for turn in turns if turn.role == "assistant"]
    assert len(assistant_turns) == 2
    assert assistant_turns[0].usage.input_tokens == 100
    assert assistant_turns[0].usage.output_tokens == 20
    assert assistant_turns[0].usage.cache_read_tokens == 0
    assert assistant_turns[1].usage.input_tokens == 50
    assert assistant_turns[1].usage.output_tokens == 10
    assert assistant_turns[1].usage.cache_read_tokens == 5


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
