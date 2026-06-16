from typer.testing import CliRunner

from tktop import __version__
from tktop.cli import app
from tktop.config import SETTINGS_FILE
from tktop.diagnostics import DiagnosticCheck, DoctorReport

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "token monitor for coding agents" in result.stdout


def test_cli_short_help():
    result = runner.invoke(app, ["-h"])

    assert result.exit_code == 0
    assert "token monitor for coding agents" in result.stdout


def test_config_short_help():
    result = runner.invoke(app, ["config", "-h"])

    assert result.exit_code == 0
    assert "Manage tktop configuration" in result.stdout


def test_cli_version():
    for option in ("--version", "-V", "-v"):
        result = runner.invoke(app, [option])

        assert result.exit_code == 0
        assert result.stdout.strip() == f"tktop {__version__}"


def test_info(monkeypatch):
    from tktop.config import Config

    monkeypatch.setattr(
        "tktop.cli.load_config",
        lambda: Config(
            session_adapter="codex",
            claude_dir="/Users/example/.claude",
            codex_dir="/Users/example/.codex",
            llm_provider="openai",
        ),
    )

    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert f"tktop {__version__}" in result.stdout
    assert "Adapter: codex" in result.stdout
    assert "Claude dir: /Users/example/.claude" in result.stdout
    assert "Codex dir: /Users/example/.codex" in result.stdout
    assert "LLM provider: openai" in result.stdout


def test_doctor_success(monkeypatch):
    async def fake_doctor():
        return DoctorReport(
            [
                DiagnosticCheck("Config", "ok", "settings file: /tmp/settings.json"),
                DiagnosticCheck("Adapter", "ok", "codex selected; 1 session(s) discovered"),
            ]
        )

    monkeypatch.setattr("tktop.cli.run_doctor", fake_doctor)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "tktop doctor" in result.stdout
    assert "[ok] Config: settings file: /tmp/settings.json" in result.stdout


def test_doctor_error_exit(monkeypatch):
    async def fake_doctor():
        return DoctorReport([DiagnosticCheck("Adapter", "error", "unknown adapter")])

    monkeypatch.setattr("tktop.cli.run_doctor", fake_doctor)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "[error] Adapter: unknown adapter" in result.stdout


def test_config_path():
    result = runner.invoke(app, ["config", "path"])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(SETTINGS_FILE)
