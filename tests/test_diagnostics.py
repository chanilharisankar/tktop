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
