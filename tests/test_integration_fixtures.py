import json
import pathlib
import shutil
from collections.abc import Iterable

from tktop.adapter.claude import ClaudeCodeAdapter
from tktop.adapter.codex import CodexAdapter
from tktop.coach.rules import build_coach_report, render_coach_markdown
from tktop.llm.prompt import build_analysis_prompt
from tktop.metrics.aggregator import aggregate
from tktop.metrics.drift import detect_drift
from tktop.metrics.pricing import calculate_cost
from tktop.metrics.types import TokenUsage


def _write_jsonl(path: pathlib.Path, entries: Iterable[dict]) -> None:
    path.write_text("\n".join(json.dumps(entry) for entry in entries))


def _write_claude_session(
    root: pathlib.Path,
    *,
    session_id: str,
    cwd: str = "/Users/testuser/Dev/myproject",
) -> pathlib.Path:
    sessions_dir = root / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "12345.json").write_text(
        json.dumps(
            {
                "pid": 12345,
                "sessionId": session_id,
                "cwd": cwd,
                "startedAt": 1779088912957,
                "version": "2.1.150",
                "status": "idle",
                "updatedAt": 1779088920000,
            }
        )
    )

    project_dir = root / "projects" / "-Users-testuser-Dev-myproject"
    project_dir.mkdir(parents=True)
    return project_dir / f"{session_id}.jsonl"


def _copy_claude_fixture(
    root: pathlib.Path,
    source: pathlib.Path,
    *,
    session_id: str,
) -> pathlib.Path:
    transcript_path = _write_claude_session(root, session_id=session_id)
    shutil.copyfile(source, transcript_path)
    return transcript_path


def _copy_codex_fixture(
    root: pathlib.Path,
    fixtures_dir: pathlib.Path,
    *,
    model: str,
) -> None:
    (root / "config.toml").write_text(f'model = "{model}"\n')
    shutil.copyfile(fixtures_dir / "codex_session_index.jsonl", root / "session_index.jsonl")

    transcript_dir = root / "sessions" / "2026" / "06" / "13"
    transcript_dir.mkdir(parents=True)
    shutil.copyfile(
        fixtures_dir / "codex_session.jsonl",
        transcript_dir / "rollout-2026-06-13T16-00-00-codex-session-001.jsonl",
    )


async def test_claude_fixture_pipeline_dedupes_message_blocks(tmp_path: pathlib.Path):
    transcript_path = _write_claude_session(tmp_path, session_id="claude-dedupe")
    usage = {
        "input_tokens": 10,
        "output_tokens": 20,
        "cache_creation_input_tokens": 100,
        "cache_read_input_tokens": 200,
    }

    def assistant_entry(content: list[dict[str, str]]) -> dict:
        return {
            "type": "assistant",
            "timestamp": "2026-06-17T12:00:00Z",
            "message": {
                "id": "msg_001",
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "usage": usage,
                "content": content,
            },
            "sessionId": "claude-dedupe",
        }

    _write_jsonl(
        transcript_path,
        [
            {
                "type": "user",
                "timestamp": "2026-06-17T11:59:55Z",
                "message": {
                    "role": "user",
                    "content": (
                        "Fix src/auth.py and run pytest tests/test_auth.py. "
                        "Stop when the login test passes."
                    ),
                },
                "sessionId": "claude-dedupe",
            },
            assistant_entry([{"type": "thinking", "thinking": "Need to inspect files."}]),
            assistant_entry([{"type": "tool_use", "id": "toolu_001", "name": "Read"}]),
            assistant_entry([{"type": "text", "text": "The adapter fix is done."}]),
        ],
    )

    adapter = ClaudeCodeAdapter(str(tmp_path))
    sessions = await adapter.discover()
    turns = await adapter.parse_transcript("claude-dedupe")
    metrics = aggregate(sessions[0], turns)
    alerts = detect_drift(turns)

    assert len(sessions) == 1
    assert sessions[0].agent_type == "claude-code"
    assert [turn.number for turn in turns] == [1, 2]
    assert len([turn for turn in turns if turn.role == "assistant"]) == 1

    assistant_turn = turns[1]
    assert assistant_turn.usage.input_tokens == 10
    assert assistant_turn.usage.output_tokens == 20
    assert assistant_turn.usage.cache_creation_tokens == 100
    assert assistant_turn.usage.cache_read_tokens == 200
    assert assistant_turn.tool_calls[0].name == "Read"
    assert "adapter fix is done" in assistant_turn.content_preview

    expected_usage = TokenUsage(
        input_tokens=10,
        output_tokens=20,
        cache_creation_tokens=100,
        cache_read_tokens=200,
    )
    assert metrics.total_usage == expected_usage
    assert metrics.total_cost == calculate_cost("claude-sonnet-4-6", expected_usage)
    assert metrics.tool_stats["Read"].calls == 1
    assert metrics.tool_stats["Read"].turns_present == 1
    assert metrics.cost_per_turn == [metrics.total_cost]
    assert alerts == []


async def test_codex_fixture_pipeline_prices_supported_model(
    tmp_path: pathlib.Path,
    fixtures_dir: pathlib.Path,
):
    _copy_codex_fixture(tmp_path, fixtures_dir, model="gpt-5.5")

    adapter = CodexAdapter(str(tmp_path))
    sessions = await adapter.discover()
    turns = await adapter.parse_transcript("codex-session-001")
    metrics = aggregate(sessions[0], turns)

    assert len(sessions) == 1
    assert sessions[0].agent_type == "codex"
    assert sessions[0].model == "gpt-5.5"
    assert sessions[0].title == "Fix login bug"
    assert [turn.role for turn in turns] == ["user", "assistant", "user", "assistant"]
    assert metrics.total_usage.input_tokens == 1_200
    assert metrics.total_usage.output_tokens == 260
    assert metrics.total_usage.cache_read_tokens == 700
    assert metrics.tool_stats["exec_command"].calls == 1
    assert metrics.total_cost > 0
    assert metrics.cost_per_turn[-1] == metrics.total_cost
    assert all(turn_cost.total > 0 for turn_cost in metrics.turn_costs)


async def test_codex_fixture_pipeline_keeps_unknown_model_tokens_without_cost(
    tmp_path: pathlib.Path,
    fixtures_dir: pathlib.Path,
):
    _copy_codex_fixture(tmp_path, fixtures_dir, model="gpt-unknown")

    adapter = CodexAdapter(str(tmp_path))
    session = (await adapter.discover())[0]
    turns = await adapter.parse_transcript("codex-session-001")
    metrics = aggregate(session, turns)

    assert metrics.total_usage.input_tokens == 1_200
    assert metrics.total_usage.output_tokens == 260
    assert metrics.total_usage.cache_read_tokens == 700
    assert metrics.total_cost == 0.0
    assert metrics.cost_per_turn == [0.0, 0.0]
    assert all(turn_cost.total == 0.0 for turn_cost in metrics.turn_costs)


async def test_coach_and_analysis_prompt_integrate_fixture_metrics(
    tmp_path: pathlib.Path,
    drift_transcript_path: pathlib.Path,
):
    _copy_claude_fixture(
        tmp_path,
        drift_transcript_path,
        session_id="test-session-003",
    )

    adapter = ClaudeCodeAdapter(str(tmp_path))
    session = (await adapter.discover())[0]
    turns = await adapter.parse_transcript("test-session-003")
    metrics = aggregate(session, turns)
    metrics.alerts = detect_drift(turns)

    report = build_coach_report(metrics)
    coach_markdown = render_coach_markdown(report)
    analysis_prompt = build_analysis_prompt(metrics)

    assert metrics.total_usage.input_tokens == 1_250
    assert metrics.total_usage.output_tokens == 850
    assert metrics.total_usage.cache_creation_tokens == 10_000
    assert metrics.total_usage.cache_read_tokens == 15_000
    assert metrics.total_cost > 0
    assert metrics.tool_stats["Read"].calls == 5
    assert {alert.type for alert in metrics.alerts} >= {"tool_loop", "read_loop"}

    assert "# Coach" in coach_markdown
    assert "## Model Fit" in coach_markdown
    assert "## Prompt Habits" in coach_markdown
    assert "## Suggested Next Prompt" in coach_markdown
    assert "estimated API-equivalent cost" in coach_markdown

    assert "## Session Data" in analysis_prompt
    assert "- Agent: claude-code" in analysis_prompt
    assert "- Input tokens: 1,250" in analysis_prompt
    assert "- Output tokens: 850" in analysis_prompt
    assert "- Estimated API-equivalent cost:" in analysis_prompt
    assert "- Read: 5 calls" in analysis_prompt
    assert "## Detected Issues" in analysis_prompt
    assert "tool_loop" in analysis_prompt
    assert "read_loop" in analysis_prompt
    assert '"fix it"' in analysis_prompt
    assert "Turn #2: out=50 tools=[Read]" in analysis_prompt
