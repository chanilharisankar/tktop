from datetime import datetime, timezone

from tktop.coach.cache import (
    build_cache_entry,
    coach_fingerprint,
    get_cached_entry,
    with_enhanced_markdown,
)
from tktop.coach.prompt import build_coach_enhancement_prompt
from tktop.coach.rules import build_coach_report, render_coach_markdown
from tktop.config import Config
from tktop.llm.labels import model_name, provider_label
from tktop.metrics.types import (
    Alert,
    SessionInfo,
    SessionMetrics,
    TokenUsage,
    ToolCall,
    ToolStat,
    Turn,
)
from tktop.tui.app import TktopApp
from tktop.tui.screens.dashboard import DashboardScreen
from tktop.tui.screens.help import HELP_TEXT

UTC = timezone.utc


def _session() -> SessionInfo:
    now = datetime(2026, 6, 17, 10, 0, tzinfo=UTC)
    return SessionInfo(
        id="coach-session",
        pid=123,
        agent_type="codex",
        project_path="/workspace/app",
        model="gpt-5",
        status="idle",
        started_at=now,
        updated_at=now,
    )


def _turn(
    number: int,
    role: str,
    preview: str,
    *,
    output_tokens: int = 0,
    tools: list[str] | None = None,
) -> Turn:
    return Turn(
        number=number,
        timestamp=datetime(2026, 6, 17, 10, number, tzinfo=UTC),
        role=role,
        model="gpt-5" if role == "assistant" else None,
        usage=TokenUsage(
            input_tokens=100 if role == "assistant" else 0,
            output_tokens=output_tokens,
        ),
        tool_calls=[
            ToolCall(name=tool_name, id=f"{number}-{index}")
            for index, tool_name in enumerate(tools or [])
        ],
        content_preview=preview,
    )


def _metrics(
    turns: list[Turn],
    tool_stats: dict[str, ToolStat] | None = None,
    alerts: list[Alert] | None = None,
) -> SessionMetrics:
    total_usage = TokenUsage()
    for turn in turns:
        total_usage.input_tokens += turn.usage.input_tokens
        total_usage.output_tokens += turn.usage.output_tokens

    default_alerts = [
        Alert(
            severity="warning",
            type="tool_loop",
            description="Read dominated exploration",
            detected_at=datetime(2026, 6, 17, 10, 0, tzinfo=UTC),
        )
    ]

    return SessionMetrics(
        session=_session(),
        turns=turns,
        total_usage=total_usage,
        total_cost=0.25,
        tool_stats=tool_stats or {},
        alerts=default_alerts if alerts is None else alerts,
    )


def test_coach_flags_broad_prompt_and_workflow_smells():
    turns = [
        _turn(1, "user", "fix auth"),
        _turn(
            2,
            "assistant",
            "Reading files",
            output_tokens=6_000,
            tools=["Read", "Read", "Read", "Read", "Read"],
        ),
        _turn(3, "assistant", "More exploration", tools=["Read", "Read", "Read", "Read"]),
        _turn(4, "assistant", "Editing now", tools=["Edit"]),
    ]
    metrics = _metrics(turns, {"Read": ToolStat(name="Read", calls=12, turns_present=2)})

    report = build_coach_report(metrics)
    titles = {finding.title for finding in report.findings}

    assert report.score < 70
    assert "First prompt was broad" in titles
    assert "No file or module scope detected" in titles
    assert "No test or validation signal detected" in titles
    assert "Heavy exploration before first edit" in titles
    assert "Read dominated tool usage" in titles


def test_coach_recognizes_scoped_validated_prompt():
    turns = [
        _turn(
            1,
            "user",
            "Inspect src/tktop/cli.py and tests/test_cli.py, add -v, and run pytest.",
        ),
        _turn(
            2,
            "assistant",
            "Implemented and ran pytest",
            output_tokens=500,
            tools=["Read", "Edit", "Bash"],
        ),
    ]
    metrics = _metrics(turns, {"Bash": ToolStat(name="Bash", calls=1, turns_present=1)})

    report = build_coach_report(metrics)
    titles = {finding.title for finding in report.findings}

    assert "Testing or validation was mentioned" in titles
    assert "First prompt was broad" not in titles
    assert report.score >= 90


def test_coach_model_fit_recommends_cheap_fast_for_simple_docs():
    turns = [
        _turn(
            1,
            "user",
            "Fix typo in README.md and run markdown lint.",
        ),
        _turn(2, "assistant", "Updated README", output_tokens=120, tools=["Read", "Edit"]),
    ]

    report = build_coach_report(_metrics(turns, alerts=[]))

    assert report.model_recommendation is not None
    assert report.model_recommendation.tier == "cheap_fast"
    assert "cheapest fast coding model" in report.model_recommendation.next_step


def test_coach_model_fit_recommends_balanced_for_focused_bug_fix():
    turns = [
        _turn(
            1,
            "user",
            "Fix failing login test in src/auth/session.py and run pytest tests/test_auth.py.",
        ),
        _turn(
            2,
            "assistant",
            "Read auth code and fixed the test failure",
            output_tokens=800,
            tools=["Read", "Edit", "Bash"],
        ),
    ]

    report = build_coach_report(_metrics(turns, alerts=[]))

    assert report.model_recommendation is not None
    assert report.model_recommendation.tier == "balanced"
    assert "balanced coding model" in report.model_recommendation.next_step


def test_coach_model_fit_recommends_strong_for_architecture_work():
    turns = [
        _turn(
            1,
            "user",
            "Design a plugin architecture and migration plan for the adapter layer.",
        ),
        _turn(2, "assistant", "Planning architecture", output_tokens=2_000, tools=["Read"]),
    ]

    report = build_coach_report(_metrics(turns, alerts=[]))

    assert report.model_recommendation is not None
    assert report.model_recommendation.tier == "strong_reasoning"
    assert "strongest reasoning model" in report.model_recommendation.next_step


def test_coach_model_fit_escalates_drift_heavy_sessions():
    turns = [_turn(1, "user", "fix auth")]
    for index in range(2, 18):
        turns.append(
            _turn(index, "assistant", "Exploring auth", output_tokens=500, tools=["Read"])
        )
    alerts = [
        Alert(
            severity="warning",
            type="tool_loop",
            description="Read dominated exploration",
            detected_at=datetime(2026, 6, 17, 10, 0, tzinfo=UTC),
        ),
        Alert(
            severity="warning",
            type="read_loop",
            description="Repeated file reads",
            detected_at=datetime(2026, 6, 17, 10, 1, tzinfo=UTC),
        ),
    ]

    report = build_coach_report(
        _metrics(turns, {"Read": ToolStat(name="Read", calls=20, turns_present=16)}, alerts)
    )

    assert report.model_recommendation is not None
    assert report.model_recommendation.tier == "strong_reasoning"
    assert any("drift alerts" in reason for reason in report.model_recommendation.reasons)


def test_coach_does_not_count_negative_test_phrase_as_validation():
    turns = [
        _turn(1, "user", "fix auth"),
        _turn(2, "assistant", "No tests were run", output_tokens=100, tools=["Edit"]),
    ]

    report = build_coach_report(_metrics(turns))

    assert any(
        finding.title == "No test or validation signal detected"
        for finding in report.findings
    )


def test_coach_recommends_checkpoint_for_long_sessions():
    turns = [_turn(1, "user", "fix auth")]
    for index in range(2, 35):
        turns.append(_turn(index, "assistant", "Working", output_tokens=100))

    report = build_coach_report(_metrics(turns))

    assert any(
        finding.title == "Long session without a checkpoint prompt"
        for finding in report.findings
    )
    assert report.suggested_next_prompt.startswith("Stop and summarize")


def test_coach_markdown_renders_findings_and_prompt_pattern():
    report = build_coach_report(_metrics([_turn(1, "user", "fix auth")]))

    markdown = render_coach_markdown(report)

    assert "# Coach" in markdown
    assert "## Model Fit" in markdown
    assert "Recommended tier" in markdown
    assert "## Prompt Habits" in markdown
    assert "## Suggested Next Prompt" in markdown
    assert "Goal: <specific change or question>" in markdown


def test_coach_enhancement_prompt_is_compact_and_contextual():
    turns = [
        _turn(1, "user", "fix auth"),
        _turn(2, "assistant", "Reading auth files", output_tokens=500, tools=["Read"]),
    ]
    metrics = _metrics(turns, {"Read": ToolStat(name="Read", calls=1, turns_present=1)})
    report = build_coach_report(metrics)

    prompt = build_coach_enhancement_prompt(metrics, report)

    assert "Top 3 Habits To Improve" in prompt
    assert "Model Tier Guidance" in prompt
    assert "Local Model Fit Recommendation" in prompt
    assert "Local Coach Findings" in prompt
    assert "Turn 1: fix auth" in prompt
    assert "Read: 1 calls" in prompt


def test_coach_cache_reuses_matching_fingerprint_and_rejects_stale_entry():
    metrics = _metrics([_turn(1, "user", "fix auth")])
    report = build_coach_report(metrics)
    entry = build_cache_entry(metrics, report, render_coach_markdown(report))
    cache = {metrics.session.id: entry}

    assert get_cached_entry(cache, metrics) == entry

    changed = _metrics([
        _turn(1, "user", "fix auth"),
        _turn(2, "assistant", "Working", output_tokens=10),
    ])
    assert coach_fingerprint(changed) != entry.fingerprint
    assert get_cached_entry(cache, changed) is None


def test_coach_cache_stores_enhanced_markdown_without_rebuilding_local_report():
    metrics = _metrics([_turn(1, "user", "fix auth")])
    report = build_coach_report(metrics)
    entry = build_cache_entry(metrics, report, render_coach_markdown(report))

    enhanced = with_enhanced_markdown(entry, "## Enhanced Coaching\n\nAdvice", "openai/gpt-4o")

    assert enhanced.report is entry.report
    assert enhanced.local_markdown == entry.local_markdown
    assert enhanced.enhanced_provider_label == "openai/gpt-4o"
    assert "Advice" in enhanced.enhanced_markdown


def test_provider_label_matches_analysis_and_coach_display():
    cfg = Config(llm_provider="openai", openai_model="gpt-4o")

    assert model_name(cfg) == "gpt-4o"
    assert provider_label(cfg) == "openai/gpt-4o"


def test_app_initializes_coach_cache():
    app = TktopApp(config=Config())

    assert app.coach_cache == {}


def test_dashboard_and_help_expose_coach_keybindings():
    dashboard_bindings = {binding.key: binding.action for binding in DashboardScreen.BINDINGS}

    assert dashboard_bindings["c"] == "coach"
    assert "Dashboard:   a analyze  c coach" in HELP_TEXT
    assert "Coach:       L enhance suggestions" in HELP_TEXT
