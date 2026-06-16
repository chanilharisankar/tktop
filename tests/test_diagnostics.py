import json

import pytest

from tktop.config import Config
from tktop.diagnostics import build_info, run_doctor


def _clear_tktop_env(monkeypatch):
    for var in (
        "TKTOP_SESSION_ADAPTER",
        "TKTOP_CLAUDE_DIR",
        "TKTOP_CODEX_DIR",
        "TKTOP_LLM_PROVIDER",
        "TKTOP_OLLAMA_HOST",
        "TKTOP_OLLAMA_MODEL",
        "TKTOP_ANTHROPIC_API_KEY",
        "TKTOP_ANTHROPIC_MODEL",
        "TKTOP_VERTEX_PROJECT",
        "TKTOP_VERTEX_REGION",
        "TKTOP_VERTEX_MODEL",
        "TKTOP_OPENAI_BASE_URL",
        "TKTOP_OPENAI_API_KEY",
        "TKTOP_OPENAI_MODEL",
        "TKTOP_SHOW_TOKEN_FLOW",
        "CLAUDE_CODE_USE_VERTEX",
        "ANTHROPIC_VERTEX_PROJECT_ID",
        "CLOUD_ML_REGION",
    ):
        monkeypatch.delenv(var, raising=False)


def _write_settings(settings_path, *, adapter="auto", claude_dir, codex_dir, provider="ollama"):
    settings_path.write_text(
        json.dumps(
            {
                "session_adapter": adapter,
                "default_provider": provider,
                "agents": {
                    "claude": {"dir": str(claude_dir)},
                    "codex": {"dir": str(codex_dir)},
                },
            }
        )
    )


def _check(report, name):
    return next(check for check in report.checks if check.name == name)


def test_build_info_includes_safe_config_summary(tmp_path):
    claude_dir = tmp_path / "claude"
    codex_dir = tmp_path / "codex"
    cfg = Config(
        session_adapter="codex",
        claude_dir=str(claude_dir),
        codex_dir=str(codex_dir),
        llm_provider="openai",
        openai_api_key="sk-secret",
    )

    info = build_info(cfg, settings_path=tmp_path / "settings.json")

    assert info.session_adapter == "codex"
    assert info.claude_dir == str(claude_dir)
    assert info.codex_dir == str(codex_dir)
    assert info.llm_provider == "openai"
    assert "sk-secret" not in repr(info)


def test_doctor_report_has_errors_only_for_error_status():
    from tktop.diagnostics import DiagnosticCheck, DoctorReport

    assert not DoctorReport(
        [
            DiagnosticCheck("Config", "ok", "created"),
            DiagnosticCheck("Codex data", "warn", "not found"),
        ]
    ).has_errors
    assert DoctorReport([DiagnosticCheck("Adapter", "error", "failed")]).has_errors


@pytest.mark.asyncio
async def test_doctor_warns_for_missing_auto_adapter_dirs(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    claude_dir = tmp_path / "missing-claude"
    codex_dir = tmp_path / "missing-codex"
    _write_settings(settings_path, claude_dir=claude_dir, codex_dir=codex_dir)

    report = await run_doctor(settings_path=settings_path)

    assert not report.has_errors
    statuses = {(check.name, check.status) for check in report.checks}
    assert ("Claude data", "warn") in statuses
    assert ("Codex data", "warn") in statuses
    assert ("Adapter", "ok") in statuses


@pytest.mark.asyncio
async def test_doctor_errors_for_data_root_that_is_file(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    claude_dir = tmp_path / ".claude"
    codex_dir = tmp_path / ".codex"
    codex_dir.write_text("not a directory")
    _write_settings(settings_path, claude_dir=claude_dir, codex_dir=codex_dir)

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    codex_check = _check(report, "Codex data")
    assert codex_check.status == "error"
    assert "not a directory" in codex_check.message


@pytest.mark.asyncio
async def test_doctor_errors_for_missing_explicit_claude_dir(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    _write_settings(
        settings_path,
        adapter="claude",
        claude_dir=tmp_path / "missing-claude",
        codex_dir=tmp_path / "missing-codex",
    )

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    assert any(
        check.name == "Adapter"
        and check.status == "error"
        and "claude adapter data dir missing" in check.message
        for check in report.checks
    )


@pytest.mark.asyncio
async def test_doctor_errors_for_missing_explicit_codex_dir(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    _write_settings(
        settings_path,
        adapter="codex",
        claude_dir=tmp_path / "missing-claude",
        codex_dir=tmp_path / "missing-codex",
    )

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    assert any(
        check.name == "Adapter"
        and check.status == "error"
        and "codex adapter data dir missing" in check.message
        for check in report.checks
    )


@pytest.mark.asyncio
async def test_doctor_errors_for_unknown_adapter(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    _write_settings(
        settings_path,
        adapter="unknown",
        claude_dir=tmp_path / ".claude",
        codex_dir=tmp_path / ".codex",
    )

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    assert any(
        check.name == "Adapter"
        and check.status == "error"
        and "unknown session adapter" in check.message
        for check in report.checks
    )


@pytest.mark.asyncio
async def test_doctor_discovers_codex_sessions(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    claude_dir = tmp_path / ".claude"
    codex_dir = tmp_path / ".codex"
    sessions_dir = codex_dir / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "rollout-codex-session-001.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-06-13T15:58:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": "codex-session-001",
                    "timestamp": "2026-06-13T15:58:00.000Z",
                    "cwd": "/workspace/project",
                    "cli_version": "0.139.0",
                },
            }
        )
        + "\n"
    )
    _write_settings(
        settings_path,
        adapter="codex",
        claude_dir=claude_dir,
        codex_dir=codex_dir,
    )

    report = await run_doctor(settings_path=settings_path)

    assert not report.has_errors
    assert any(
        check.name == "Adapter"
        and check.status == "ok"
        and "1 session(s) discovered" in check.message
        for check in report.checks
    )


@pytest.mark.asyncio
async def test_doctor_reports_adapter_discovery_failure(tmp_path, monkeypatch):
    class FailingAdapter:
        name = "failing"

        async def discover(self):
            raise OSError("cannot read sessions")

    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{}")
    monkeypatch.setattr(
        "tktop.diagnostics.load_config",
        lambda settings_path=None: Config(
            session_adapter="auto",
            claude_dir="/Users/example/.claude",
            codex_dir="/Users/example/.codex",
            llm_provider="ollama",
        ),
    )
    monkeypatch.setattr("tktop.diagnostics.create_adapter", lambda cfg: FailingAdapter())

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    adapter_check = _check(report, "Adapter")
    assert adapter_check.status == "error"
    assert "discovery failed: cannot read sessions" in adapter_check.message


@pytest.mark.asyncio
async def test_doctor_warns_for_missing_selected_openai_key(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    codex_dir = tmp_path / ".codex"
    (codex_dir / "sessions").mkdir(parents=True)
    _write_settings(
        settings_path,
        adapter="codex",
        claude_dir=tmp_path / ".claude",
        codex_dir=codex_dir,
        provider="openai",
    )

    report = await run_doctor(settings_path=settings_path)

    assert not report.has_errors
    assert any(
        check.name == "LLM provider"
        and check.status == "warn"
        and "openai API key missing" in check.message
        for check in report.checks
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "provider_settings", "expected_status", "expected_message"),
    [
        ("ollama", {"host": ""}, "warn", "ollama host is not configured"),
        ("anthropic", {"api_key": "sk-ant-test"}, "ok", "anthropic API key configured"),
        ("vertex", {"project": "project-1", "region": "us-east5"}, "ok", "project-1/us-east5"),
        (
            "openai",
            {"base_url": "https://api.openai.example/v1", "api_key": "sk-test"},
            "ok",
            "https://api.openai.example/v1",
        ),
    ],
)
async def test_doctor_reports_selected_provider_status(
    tmp_path,
    monkeypatch,
    provider,
    provider_settings,
    expected_status,
    expected_message,
):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    codex_dir = tmp_path / ".codex"
    (codex_dir / "sessions").mkdir(parents=True)
    settings = {
        "session_adapter": "codex",
        "default_provider": provider,
        "agents": {
            "claude": {"dir": str(tmp_path / ".claude")},
            "codex": {"dir": str(codex_dir)},
        },
        "providers": {
            provider: provider_settings,
        },
    }
    settings_path.write_text(json.dumps(settings))

    report = await run_doctor(settings_path=settings_path)

    provider_check = _check(report, "LLM provider")
    assert provider_check.status == expected_status
    assert expected_message in provider_check.message


@pytest.mark.asyncio
async def test_doctor_errors_for_unknown_provider(tmp_path, monkeypatch):
    _clear_tktop_env(monkeypatch)
    settings_path = tmp_path / "settings.json"
    codex_dir = tmp_path / ".codex"
    (codex_dir / "sessions").mkdir(parents=True)
    _write_settings(
        settings_path,
        adapter="codex",
        claude_dir=tmp_path / ".claude",
        codex_dir=codex_dir,
        provider="unknown",
    )

    report = await run_doctor(settings_path=settings_path)

    assert report.has_errors
    assert any(
        check.name == "LLM provider" and check.status == "error"
        for check in report.checks
    )
